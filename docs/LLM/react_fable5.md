# useReducer によるカウンター実装の解説

React の `useReducer` フックを使ったカウンターコンポーネントを、
**3つのブロック（初期状態 / reducer 関数 / コンポーネント本体）** に分けて解説する。

> ⚠️ 元コードの `const Counter => () {` は構文エラー。
> 正しくは `const Counter = () => {`（アロー関数の定義）である。以下は修正済みのコードで解説する。

---

## ブロック1: 初期状態（initialState）

```jsx
const initialState = { count: 0 };
```

| 行 | コード | 解説 |
|---|---|---|
| 1 | `const initialState = { count: 0 };` | state（状態）の初期値を定義する。`count` プロパティを持つオブジェクトで、初期値は `0`。`useReducer` の第2引数として渡される |

- state をオブジェクトにしておくことで、後からプロパティ（例: `step` や `history`）を追加しやすい。
- コンポーネントの外で定義しているため、再レンダリングのたびに再生成されない。

---

## ブロック2: reducer 関数

```jsx
const reducer = (state, action) => {
  switch (action.type) {
    case 'increment':
      return { count: state.count + 1 };
    case 'decrement':
      return { count: state.count - 1 };
    default:
      throw new Error();
  }
};
```

| 行 | コード | 解説 |
|---|---|---|
| 1 | `const reducer = (state, action) => {` | reducer 関数の定義。**現在の state** と **action（何をしたいかを表すオブジェクト）** を受け取り、**新しい state を返す**純粋関数 |
| 2 | `switch (action.type) {` | `action.type`（アクションの種類を表す文字列）によって処理を分岐する |
| 3 | `case 'increment':` | `type` が `'increment'`（増加）のときの分岐 |
| 4 | `return { count: state.count + 1 };` | 現在の `count` に 1 を足した**新しいオブジェクト**を返す。既存の state を直接書き換えず、新しいオブジェクトを作るのが React の原則（イミュータブル更新） |
| 5 | `case 'decrement':` | `type` が `'decrement'`（減少）のときの分岐 |
| 6 | `return { count: state.count - 1 };` | 現在の `count` から 1 を引いた新しいオブジェクトを返す |
| 7 | `default:` | 上記のどの `case` にも一致しない `type` が渡されたときの分岐 |
| 8 | `throw new Error();` | 未知のアクションは例外を投げてバグを早期発見する。（何もせず `return state;` する設計もある） |

### reducer のポイント
- **純粋関数**であること: 同じ `state` と `action` を渡せば必ず同じ結果を返す。副作用（API 呼び出しなど）を含めてはいけない。
- `return` した値が**そのまま次の state** になる。

---

## ブロック3: Counter コンポーネント

```jsx
const Counter = () => {   // ← 元コードの「const Counter => () {」は構文エラーなので修正
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <>
      Count: {state.count}
      <button onClick={() => dispatch({ type: 'decrement' })}>-</button>
      <button onClick={() => dispatch({ type: 'increment' })}>+</button>
    </>
  );
};
```

| 行 | コード | 解説 |
|---|---|---|
| 1 | `const Counter = () => {` | 関数コンポーネントの定義。アロー関数で書く場合は `= () =>` の順になる点に注意 |
| 2 | `const [state, dispatch] = useReducer(reducer, initialState);` | `useReducer` フックを呼び出す。第1引数に reducer 関数、第2引数に初期状態を渡す。戻り値は配列で、分割代入により **`state`（現在の状態）** と **`dispatch`（アクションを送信する関数）** を受け取る |
| 3 | `return (` | JSX の返却開始。複数行の JSX は `( )` で囲む |
| 4 | `<>` | **フラグメント**（`React.Fragment` の省略記法）。余分な DOM 要素（`<div>` など）を追加せずに複数の要素をまとめて返すために使う |
| 5 | `Count: {state.count}` | 現在のカウント値を表示。`{ }` 内は JavaScript 式として評価され、`state.count` の値が描画される |
| 6 | `<button onClick={() => dispatch({ type: 'decrement' })}>-</button>` | 「−」ボタン。クリックすると `dispatch` に `{ type: 'decrement' }` を渡す → reducer が呼ばれ `count` が 1 減る → 新しい state で再レンダリングされる |
| 7 | `<button onClick={() => dispatch({ type: 'increment' })}>+</button>` | 「＋」ボタン。クリックすると `{ type: 'increment' }` が dispatch され、`count` が 1 増える |
| 8 | `</>` | フラグメントの閉じタグ |
| 9 | `);` | JSX 返却の終了 |
| 10 | `};` | コンポーネント定義の終了 |

---

## 全体の動作フロー

```
ボタンクリック
  → dispatch({ type: 'increment' }) を呼ぶ
  → React が reducer(現在のstate, action) を実行
  → reducer が新しい state（例: { count: 1 }）を返す
  → state が更新され、コンポーネントが再レンダリング
  → 画面の「Count: 1」が更新される
```

## useState との違い

| 観点 | useState | useReducer |
|---|---|---|
| 更新方法 | `setCount(count + 1)` を直接呼ぶ | `dispatch(action)` でアクションを送り、更新ロジックは reducer に集約 |
| 向いている場面 | 単純な状態 | 更新パターンが複数ある・状態遷移のロジックを一箇所にまとめたい場合 |
| テスト | コンポーネントごと | reducer は純粋関数なので単体テストが容易 |

- 補足: 元コードで直すべき点は 1 箇所だけで、const Counter => () { → const Counter = () => { です。
- また useReducer を使うには import { useReducer } from 'react'; が必要です。