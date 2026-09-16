import { describe, expect, it } from 'vitest';
import {
  DEFAULT_OPTION_FALLBACK,
  MODEL_LABEL_PREFIX,
  defaultOptionLabel,
  formatModelLabel,
  modelOptionLabel,
} from './modelLabel';
import type { ModelInfo } from '../types';

const info = (over: Partial<ModelInfo> = {}): ModelInfo => ({
  model: 'claude-sonnet-5',
  light_model: 'claude-haiku-4-5-20251001',
  heavy_model: '',
  chunking_model: 'claude-haiku-4-5',
  qa_model: 'claude-sonnet-5',
  ...over,
});

describe('formatModelLabel', () => {
  it('取得できていれば既定モデル名を出す', () => {
    expect(formatModelLabel(info())).toBe('claude-sonnet-5');
  });

  it('未取得・取得失敗（null）は何も出さない', () => {
    // 「利用モデル名：」だけがヘッダーに残るのを防ぐ
    expect(formatModelLabel(null)).toBeNull();
  });

  it('モデル名が空文字でも何も出さない', () => {
    expect(formatModelLabel(info({ model: '   ' }))).toBeNull();
  });

  it('論理層だけ別モデルなら併記する（ヘッダーが嘘をつかない）', () => {
    expect(formatModelLabel(info({ heavy_model: 'claude-opus-5' }))).toBe(
      'claude-sonnet-5（論理層: claude-opus-5）',
    );
  });

  it('論理層が主モデルと同じなら併記しない（冗長なだけ）', () => {
    expect(formatModelLabel(info({ heavy_model: 'claude-sonnet-5' }))).toBe('claude-sonnet-5');
  });

  it('見出しは固定文字列', () => {
    expect(MODEL_LABEL_PREFIX).toBe('利用モデル名：');
  });
});

describe('defaultOptionLabel', () => {
  it('既定値が分かっていれば名前まで出す', () => {
    expect(defaultOptionLabel('claude-sonnet-5')).toBe('（既定値: claude-sonnet-5）');
  });

  it('未取得なら「（既定値）」だけにする', () => {
    // 分からない名前をでっち上げない。フロントに既定値を持たせないための分岐
    expect(defaultOptionLabel('')).toBe(DEFAULT_OPTION_FALLBACK);
    expect(defaultOptionLabel('   ')).toBe(DEFAULT_OPTION_FALLBACK);
  });
});

describe('modelOptionLabel', () => {
  it('モデル名に単価を添える（どれが高いか画面で分かる）', () => {
    expect(
      modelOptionLabel({ id: 'claude-opus-5', input_price: 0.005, output_price: 0.025 }),
    ).toBe('claude-opus-5（入力 $0.005／出力 $0.025 per 1K）');
  });
});
