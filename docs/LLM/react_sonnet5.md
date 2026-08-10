# React Q&A ログ（Claude Sonnet 5）

Claude Sonnet 5 との React 関連のやり取りを記録したドキュメント。

---

## Q1. `useReducer` を使ったカウンターコンポーネントの解説

### 質問

以下のReactのコードを、ブロックごと、1行ずつ解説してほしい。

```jsx
const initialState = { count: 0 };

const reducer = (state, action) => {
  switch (action.type) {
    case 'increment':
      return {count: state.count + 1};
    case 'decrement':
      return {count: state.count - 1};
    default:
      throw new Error();
  }
}

const Counter => () {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <>
      Count: {state.count}
      <button onClick={() => dispatch({type: 'decrement'})}>-</button>
      <button onClick={() => dispatch({type: 'increment'})}>+</button>
    </>
  );
}
```

### 回答

このコードは `useReducer` を使ったカウンターの実装。ブロックごとに解説する。

#### 1. 初期状態の定義

```jsx
const initialState = { count: 0 };
```

- `useReducer` に渡す**初期状態オブジェクト**。
- `count` という数値プロパティを持つオブジェクトとして状態を管理する（単なる数値ではなくオブジェクトにしているのは、将来的に他のプロパティを追加しやすくするためのReducerパターンの定石）。

#### 2. Reducer関数

```jsx
const reducer = (state, action) => {
  switch (action.type) {
    case 'increment':
      return {count: state.count + 1};
    case 'decrement':
      return {count: state.count - 1};
    default:
      throw new Error();
  }
}
```

- `reducer` は `(現在の状態, アクション) → 次の状態` という**純粋関数**。React自体はこれを呼び出すだけで、状態更新のロジックはすべてこの関数の中に集約される。
- `action.type` によって処理を分岐する `switch` 文が典型パターン。
  - `'increment'` → `count` を1増やした**新しいオブジェクト**を返す。
  - `'decrement'` → `count` を1減らした**新しいオブジェクト**を返す。
  - どちらにも一致しない `type` が来た場合は `default` で `Error` を投げる（想定外のアクションを早期に検知するためのガード）。
- **重要な点**：`state.count + 1` のように既存の `state` を直接書き換えず、`{count: ...}` という新しいオブジェクトを `return` している。Reactは状態の参照（reference）が変わったことを検知して再レンダリングするため、必ず新しいオブジェクトを返す必要がある（イミュータブルな更新）。

#### 3. Counterコンポーネント

```jsx
const Counter => () {
```

- ここに**構文エラー**がある。アロー関数の書き方が誤っている。正しくは以下。

```jsx
const Counter = () => {
```

`=>` の前に `=` が抜けているため、このままではビルドが通らない。以降は「意図通り修正されている」前提で解説する。

```jsx
  const [state, dispatch] = useReducer(reducer, initialState);
```

- `useReducer(reducer関数, 初期状態)` を呼び出し、2つの値を配列分割代入で受け取る。
  - `state`：現在の状態（最初は `{ count: 0 }`）。
  - `dispatch`：アクションを送出するための関数。`dispatch(action)` を呼ぶと、内部で `reducer(現在のstate, action)` が実行され、戻り値が新しい `state` として保存され、コンポーネントが再レンダリングされる。
- `useState` との違いは、状態更新ロジックを `reducer` 関数に集約できる点。状態遷移が複雑になる（アクションの種類が増える、複数の値が絡み合う）ケースで有利。

```jsx
  return (
    <>
      Count: {state.count}
```

- `<>...</>` は **Fragment**（余分なDOM要素を作らずに複数要素をまとめるための書き方）。
- `{state.count}` で現在のカウント値をJSX内に埋め込んで表示している。

```jsx
      <button onClick={() => dispatch({type: 'decrement'})}>-</button>
      <button onClick={() => dispatch({type: 'increment'})}>+</button>
```

- 2つのボタンがあり、それぞれクリック時に `dispatch` を呼び出す。
- `onClick={() => dispatch(...)}` のように**アロー関数でラップ**しているのは、`onClick={dispatch({type: 'decrement'})}` と書くと**レンダリング時に即座に実行されてしまう**ため。クリックされた時点で実行したいので、クリックイベントが発生するまで実行を遅延させる無名関数でラップする。
- `dispatch({type: 'decrement'})` を呼ぶと `reducer(state, {type: 'decrement'})` が実行され、`{count: state.count - 1}` が新しい状態になる。`increment` ボタンも同様に `+1` される。

```jsx
    </>
  );
}
```

- Fragmentとコンポーネント関数を閉じている。

#### まとめの流れ

1. ボタンクリック → `dispatch({type: 'increment' or 'decrement'})` が呼ばれる
2. Reactが内部で `reducer(現在のstate, action)` を実行
3. `reducer` が新しい `state` オブジェクトを返す
4. Reactがその新しい `state` で `Counter` を再レンダリング
5. `{state.count}` の表示が更新される

**注意点**：`const Counter => () {` は構文エラーなので、実際に動かす際は `const Counter = () => {` に修正が必要。

---

## Q2. Claude モデルの料金比較（Fable 5 / Opus 5 / Sonnet 5 / Haiku 4.5）

### 質問

Fable5. Opus5, Sonnet5, Haiku4.5 の料金の比較をしてください。

### 回答

`claude-api` スキルを読み込んで、正確な最新の料金情報を確認。

4モデルの料金比較（Anthropic first-party API料金、2026-08-09時点）：

| モデル | モデルID | コンテキスト | 最大出力 | Input（$/1Mトークン） | Output（$/1Mトークン） |
|---|---|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | 1M | 128K | $10.00 | $50.00 |
| Claude Opus 5 | `claude-opus-5` | 1M | 128K | $5.00 | $25.00 |
| Claude Sonnet 5 | `claude-sonnet-5` | 1M | 128K | $3.00（$2.00 — 2026-08-31まで導入価格） | $15.00（$10.00 — 導入価格） |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | 64K | $1.00 | $5.00 |

#### ポイント

- **料金の傾き**：Haiku 4.5 を基準（1x）とすると、Sonnet 5 が約3x（導入価格なら2x）、Opus 5 が5x、Fable 5 が10x という価格差になる。
- **Sonnet 5 は今だけ割安**：本日（2026-08-09）時点では導入価格（Input $2 / Output $10）が適用中で、通常価格（$3 / $15）は2026-08-31以降。
- **Fable 5** はAnthropicの最も高性能なモデルで、思考が常時オン（`thinking`パラメータ省略可）、生の思考過程は返らず要約のみ。30日以上のデータ保持が必須（ゼロデータ保持不可）。
- **Opus 5** はOpus 4.8からの直接アップグレード相当で、同じ$5/$25価格帯のまま。思考がデフォルトでオン。
- **Sonnet 5** はコスト効率重視で、コーディング・エージェント系タスクでOpus級の性能に近づいている。
- **Haiku 4.5** は最速・最安で、コンテキスト窓も200K（他は1M）とやや小さめ。

#### 使い分けの目安

- **最高性能が必要／長時間の自律タスク**：Fable 5
- **通常のエージェント・コーディング用途のデフォルト**：Opus 5（このスキルの既定推奨）
- **コスト重視でOpus級品質が欲しい場合**：Sonnet 5（特に今は導入価格でお得）
- **単純作業・低レイテンシ・サブエージェント**：Haiku 4.5
