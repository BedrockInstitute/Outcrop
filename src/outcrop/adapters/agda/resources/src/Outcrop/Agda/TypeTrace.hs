{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE TypeApplications #-}

-- | Optional type trace used by the Outcrop document renderer.
-- The upstream checker behaves exactly as before unless
-- @OUTCROP_AGDA_TYPES@ names an output file.
module Outcrop.Agda.TypeTrace
  ( traceCheckedType
  , traceType
  , traceDeclaration
  , flushPendingTypes
  , flushTypeTrace
  ) where

import Control.Concurrent.MVar
import Control.Exception (IOException, try)
import Control.Monad.IO.Class (liftIO)
import Control.Monad (forM_, when)
import Data.Aeson (encode, object, (.=))
import Data.Bits (xor)
import qualified Data.ByteString as BS
import qualified Data.ByteString.Lazy.Char8 as LBS
import qualified Data.Map.Strict as Map
import Data.Monoid (Any(..))
import Data.Word (Word32, Word64)
import Numeric (showHex)
import System.Environment (lookupEnv)
import System.IO
import System.IO.Unsafe (unsafePerformIO)

import Agda.Syntax.Internal (Type, Term(Dummy))
import qualified Agda.Syntax.Abstract as A
import qualified Agda.Syntax.Concrete as C
import Agda.Syntax.Internal.Generic (foldTerm)
import Agda.Syntax.Position
import Agda.TypeChecking.Monad (TCM, Closure, buildClosure, enterClosure, asksTC, envCheckingWhere)
import Agda.TypeChecking.Pretty (prettyTCM)
import Agda.Utils.FileName (filePath)
import qualified Agda.Utils.Maybe.Strict as Strict
import Agda.Syntax.Common.Pretty (prettyShow)

data TraceSink = TraceDisabled | TraceSink Handle String

type TraceKey = (FilePath, Word32, Word32, String)

data PendingType = PendingType
  { pendingKey     :: TraceKey
  , pendingHash    :: String
  , pendingClosure :: Closure Type
  }

{-# NOINLINE traceSink #-}
traceSink :: MVar (Maybe TraceSink)
traceSink = unsafePerformIO $ newMVar Nothing

{-# NOINLINE sourceHashes #-}
sourceHashes :: MVar (Map.Map FilePath String)
sourceHashes = unsafePerformIO $ newMVar Map.empty

{-# NOINLINE pendingTypes #-}
pendingTypes :: MVar (Map.Map TraceKey PendingType)
pendingTypes = unsafePerformIO $ newMVar Map.empty

{-# NOINLINE writtenTypes #-}
writtenTypes :: MVar (Map.Map TraceKey ())
writtenTypes = unsafePerformIO $ newMVar Map.empty

sourceHash :: FilePath -> IO String
sourceHash path = modifyMVar sourceHashes $ \ hashes -> case Map.lookup path hashes of
  Just value -> pure (hashes, value)
  Nothing -> do
    bytes <- BS.readFile path
    let value = showHex (BS.foldl' step offset bytes) ""
        offset = 14695981039346656037 :: Word64
        step hash byte = (hash `xor` fromIntegral byte) * 1099511628211
    pure (Map.insert path value hashes, value)

getTraceSink :: IO TraceSink
getTraceSink = modifyMVar traceSink $ \case
  Just sink -> pure (Just sink, sink)
  Nothing -> do
    path <- lookupEnv "OUTCROP_AGDA_TYPES"
    sink <- case path of
      Nothing -> pure TraceDisabled
      Just output -> do
        handle <- openFile output AppendMode
        hSetBuffering handle $ BlockBuffering $ Just (1024 * 1024)
        run <- maybe "default" id <$> lookupEnv "OUTCROP_AGDA_RUN"
        pure $ TraceSink handle run
    pure (Just sink, sink)

recordCheckedType :: HasRange a => String -> a -> Type -> TCM b -> TCM b
recordCheckedType kind value type_ action = do
  result <- action
  recordType kind value type_
  pure result

recordType :: HasRange a => String -> a -> Type -> TCM ()
recordType kind value type_ = case rangeToIntervalWithFile $ continuous $ getRange value of
  Nothing -> pure ()
  Just interval -> case srcFile $ iStart interval of
    Strict.Nothing -> pure ()
    Strict.Just source -> do
      sink <- liftIO getTraceSink
      case sink of
        TraceDisabled -> pure ()
        -- Module applications check their telescope with a dummy result type.
        -- Neither a complete nor a partial module application is a term with
        -- that type. Do not queue its placeholder (including one under a Pi),
        -- or reserve the key against a later genuine type judgement.
        TraceSink _ _ | getAny (foldTerm isDummy type_) -> pure ()
        TraceSink _ _ -> do
          let path = filePath (rangeFilePath source)
          hash <- liftIO $ sourceHash path
          let key = (path, posPos (iStart interval), posPos (iEnd interval), kind)
          written <- liftIO $ Map.member key <$> readMVar writtenTypes
          queued <- liftIO $ Map.member key <$> readMVar pendingTypes
          if written || queued then pure () else do
            closure <- buildClosure type_
            liftIO $ modifyMVar_ pendingTypes $ pure . Map.insert key (PendingType key hash closure)

isDummy :: Term -> Any
isDummy Dummy{} = Any True
isDummy _       = Any False

traceCheckedType :: HasRange a => String -> a -> Type -> TCM b -> TCM b
traceCheckedType = recordCheckedType

traceType :: HasRange a => String -> a -> Type -> TCM ()
traceType = recordType

-- | Declaration boundaries come from the checked language's abstract syntax,
-- not from Markdown or a scan for equals signs. Where-local declarations are
-- part of their enclosing definition, not independently marked definitions.
traceDeclaration :: A.Declaration -> TCM ()
traceDeclaration declaration = case declaration of
  -- The nicifier gives an inferred underscore the name's own range. An
  -- explicitly authored type (including an explicit _) has its own range.
  A.Axiom _ _ _ _ name type_
    | getRange type_ /= noRange
    , getRange type_ /= A.nameBindingSite (A.qnameName name) ->
    recordSpan "signature" $ fuseRange (A.nameBindingSite $ A.qnameName name) type_
  A.FunDef _ name clauses -> do
    checkingWhere <- asksTC envCheckingWhere
    when (checkingWhere == C.NoWhere_ && any (hasEquation . A.clauseRHS) clauses) $
      recordSpan "definition-end" $ fuseRange (A.nameBindingSite $ A.qnameName name) clauses
  _ -> pure ()
  where
    hasEquation A.RHS{} = True
    hasEquation A.AbsurdRHS = False
    hasEquation (A.WithRHS _ _ clauses) = any (hasEquation . A.clauseRHS) clauses
    hasEquation (A.RewriteRHS _ _ rhs _) = hasEquation rhs

recordSpan :: String -> Range -> TCM ()
recordSpan kind range = case rangeToIntervalWithFile $ continuous range of
  Nothing -> pure ()
  Just interval -> case srcFile $ iStart interval of
    Strict.Nothing -> pure ()
    Strict.Just source -> liftIO $ do
      sink <- getTraceSink
      case sink of
        TraceDisabled -> pure ()
        TraceSink handle run -> do
          let path = filePath (rangeFilePath source)
              start = posPos (iStart interval)
              end = posPos (iEnd interval)
              key = (path, start, end, kind)
          hash <- sourceHash path
          written <- Map.member key <$> readMVar writtenTypes
          when (not written) $ do
            let record = object
                  [ "version" .= (1 :: Int), "run" .= run, "kind" .= kind
                  , "path" .= path, "sourceHash" .= hash
                  , "start" .= start, "end" .= end, "type" .= ("" :: String) ]
            _ <- try @IOException $ LBS.hPutStrLn handle (encode record)
            modifyMVar_ writtenTypes $ pure . Map.insert key ()

flushPendingTypes :: TCM ()
flushPendingTypes = do
  sink <- liftIO getTraceSink
  case sink of
    TraceDisabled -> pure ()
    TraceSink handle run -> do
      pending <- liftIO $ modifyMVar pendingTypes $ \ values -> pure (Map.empty, Map.elems values)
      forM_ pending $ \ (PendingType key@(path, start, end, kind) hash closure) -> do
        rendered <- prettyShow <$> enterClosure closure prettyTCM
        let withRun = encode $ object
              [ "version" .= (1 :: Int)
              , "run" .= run
              , "kind" .= kind
              , "path" .= path
              , "sourceHash" .= hash
              , "start" .= start
              , "end" .= end
              , "type" .= rendered
              ]
        liftIO $ do
          _ <- try @IOException $ LBS.hPutStrLn handle withRun
          modifyMVar_ writtenTypes $ pure . Map.insert key ()

flushTypeTrace :: IO ()
flushTypeTrace = withMVar traceSink $ \case
  Just (TraceSink handle _) -> hFlush handle
  _                         -> pure ()
