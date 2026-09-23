import { describe, expect, it } from 'vitest';
import {
  INITIAL_HEADER_MODELS,
  headerModelOptions,
  headerSelectValue,
  heavyModelNote,
  isModelTab,
} from './headerModel';
import type { ModelChoice } from '../types';

const choice = (id: string, input = 0.002, output = 0.01): ModelChoice => ({
  id,
  input_price: input,
  output_price: output,
  context_window: 1000000,
  max_output: 128000,
});

describe('isModelTab', () => {
  it('エージェントの 3 タブはヘッダーでモデルを選ぶ', () => {
    expect(isModelTab('basic')).toBe(true);
    expect(isModelTab('support')).toBe(true);
    expect(isModelTab('review')).toBe(true);
  });

  it('データ管理タブは対象外（工程ごとに既定モデルが違う）', () => {
    expect(isModelTab('data')).toBe(false);
  });
});

describe('INITIAL_HEADER_MODELS', () => {
  it('初期状態はすべて未選択（= サーバーの既定値）', () => {
    expect(INITIAL_HEADER_MODELS).toEqual({ basic: '', support: '', review: '' });
  });
});

describe('headerSelectValue', () => {
  it('未選択ならサーバーの既定モデル名を表示する（空欄にしない）', () => {
    expect(headerSelectValue('', 'claude-sonnet-5')).toBe('claude-sonnet-5');
  });

  it('選んだモデルがあればそれを表示する', () => {
    expect(headerSelectValue('claude-opus-5-5', 'claude-sonnet-5')).toBe('claude-opus-5-5');
  });

  it('既定値も未取得なら空文字', () => {
    expect(headerSelectValue('', '')).toBe('');
  });
});

describe('headerModelOptions', () => {
  const models = [choice('claude-opus-5-5', 0.004, 0.02), choice('claude-sonnet-5')];

  it('一覧の順に単価つきラベルを付ける', () => {
    expect(headerModelOptions(models, 'claude-sonnet-5')).toEqual([
      { id: 'claude-opus-5-5', label: 'claude-opus-5-5（入力 $0.004／出力 $0.02 per 1K）' },
      { id: 'claude-sonnet-5', label: 'claude-sonnet-5（入力 $0.002／出力 $0.01 per 1K）' },
    ]);
  });

  it('既定モデルが一覧に無ければ先頭に足す（表示が別モデルへずれない）', () => {
    const options = headerModelOptions(models, 'claude-sonnet-4-6');
    expect(options[0]).toEqual({ id: 'claude-sonnet-4-6', label: 'claude-sonnet-4-6' });
    expect(options).toHaveLength(3);
  });

  it('既定モデルが未取得なら足さない', () => {
    expect(headerModelOptions(models, '')).toHaveLength(2);
  });

  it('一覧が取れなくても既定モデルだけは出す', () => {
    expect(headerModelOptions([], 'claude-sonnet-5')).toEqual([
      { id: 'claude-sonnet-5', label: 'claude-sonnet-5' },
    ]);
  });
});

describe('heavyModelNote', () => {
  it('論理層のモデルが無ければ注記しない', () => {
    expect(heavyModelNote('claude-sonnet-5', '')).toBeNull();
  });

  it('同じモデルなら注記しない', () => {
    expect(heavyModelNote('claude-sonnet-5', 'claude-sonnet-5')).toBeNull();
  });

  it('別モデルなら注記する（隠すとヘッダーが実挙動について嘘をつく）', () => {
    expect(heavyModelNote('claude-sonnet-5', 'claude-opus-5-5')).toBe('（論理層: claude-opus-5-5）');
  });
});
