import { describe, expect, it } from 'vitest';
import { MODEL_LABEL_PREFIX, embeddingLabel, modelOptionLabel } from './modelLabel';

describe('MODEL_LABEL_PREFIX', () => {
  it('見出しは固定文字列', () => {
    expect(MODEL_LABEL_PREFIX).toBe('利用モデル名：');
  });
});

describe('modelOptionLabel', () => {
  it('モデル名に単価を添える（どれが高いか画面で分かる）', () => {
    expect(
      modelOptionLabel({ id: 'claude-opus-5-5', input_price: 0.004, output_price: 0.02 }),
    ).toBe('claude-opus-5-5（入力 $0.004／出力 $0.02 per 1K）');
  });
});

describe('embeddingLabel', () => {
  it('モデル名と次元を API の値のまま出す（画面にモデル名を持たない）', () => {
    expect(embeddingLabel({ embedding_model: 'm-embed', embedding_dims: 3072 })).toBe(
      'm-embed・3072 次元',
    );
  });

  it('次元が 0（旧サーバー）ならモデル名だけ', () => {
    expect(embeddingLabel({ embedding_model: 'm-embed', embedding_dims: 0 })).toBe('m-embed');
  });

  it('未取得・空文字なら空文字（注記はモデル名なしで出す）', () => {
    expect(embeddingLabel(null)).toBe('');
    expect(embeddingLabel({ embedding_model: '', embedding_dims: 3072 })).toBe('');
  });
});
