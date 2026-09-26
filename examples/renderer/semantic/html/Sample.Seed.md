<pre class="Agda"><a id="9" class="Symbol">{-#</a> <a id="13" class="Keyword">OPTIONS</a> <a id="21" class="Pragma">--cubical</a> <a id="31" class="Pragma">--safe</a> <a id="38" class="Pragma">--guardedness</a> <a id="52" class="Symbol">#-}</a>
<a id="56" class="Keyword">module</a> <a id="63" href="Sample.Seed.html" class="Module">Sample.Seed</a> <a id="75" class="Keyword">where</a>
</pre>
<!--en-->
# A small input
<!--zh-->
# 一个小输入
<!--ja-->
# 小さな入力
<!--/-->

<!--en-->
Our [marker]{.term-intro #marker} is a value with one constructor. The example supplies real definition links and signatures without importing a mathematical library.

## The marker type

The declaration below specifies its only constructor.

**Definition** (`Marker`{.Agda}) The type contains the constructor `mark`{.Agda}.
<!--zh-->
这里的[标记]{.term-intro #marker}是只有一个构造子的值。本例无需导入数学库，就能提供真实的定义链接和类型签名。

## 标记类型

下面的声明指定唯一的构造子。

**定义** (`Marker`{.Agda}) 该类型具有构造子 `mark`{.Agda}。
<!--ja-->
ここでの[印]{.term-intro #marker}は一つの構成子を持つ値である。数学ライブラリを導入せず，実際の定義リンクと型を提供する。

## 印の型

次の宣言で唯一の構成子を指定する。

**定義** (`Marker`{.Agda}) この型は構成子 `mark`{.Agda}を持つ。
<!--/-->

<pre class="Agda"><a id="825" class="Keyword">data</a> <a id="Marker"></a><a id="830" href="Sample.Seed.html#830" class="Datatype">Marker</a> <a id="837" class="Symbol">:</a> <a id="839" href="Agda.Primitive.html#388" class="Primitive">Set</a> <a id="843" class="Keyword">where</a>
  <a id="Marker.mark"></a><a id="851" href="Sample.Seed.html#851" class="InductiveConstructor">mark</a> <a id="856" class="Symbol">:</a> <a id="858" href="Sample.Seed.html#830" class="Datatype">Marker</a>
</pre>

<!--en-->
## Returning an input

The next function returns the supplied marker unchanged.

**Definition** (`keep`{.Agda}) The result is the input.
<!--zh-->
## 返回输入

下一个函数原样返回给定的标记。

**定义** (`keep`{.Agda}) 结果就是输入。
<!--ja-->
## 入力を返す

次の関数は与えられた印をそのまま返す。

**定義** (`keep`{.Agda}) 結果は入力そのものである。
<!--/-->

<pre class="Agda"><a id="keep"></a><a id="1181" href="Sample.Seed.html#1181" class="Function">keep</a> <a id="1186" class="Symbol">:</a> <a id="1188" href="Sample.Seed.html#830" class="Datatype">Marker</a> <a id="1195" class="Symbol">→</a> <a id="1197" href="Sample.Seed.html#830" class="Datatype">Marker</a>
<a id="1204" href="Sample.Seed.html#1181" class="Function">keep</a> <a id="1209" href="Sample.Seed.html#1209" class="Bound">value</a> <a id="1215" class="Symbol">=</a> <a id="1217" href="Sample.Seed.html#1209" class="Bound">value</a>
</pre>

<!--en-->
The [next chapter](Sample.Use.html#sec-1) applies this function twice.
<!--zh-->
[下一章](Sample.Use.html#sec-1)会把这个函数连续应用两次。
<!--ja-->
[次の章](Sample.Use.html#sec-1)ではこの関数を二回適用する。
<!--/-->
