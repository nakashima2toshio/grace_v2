import { describe, expect, it } from 'vitest';
import { MODEL_LABEL_PREFIX, modelOptionLabel } from './modelLabel';

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
