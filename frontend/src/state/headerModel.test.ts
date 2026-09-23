import { describe, expect, it } from 'vitest';
import {
  INITIAL_HEADER_MODELS,
  headerModelOptions,
  headerSelectValue,
  heavyModelNote,
  headerSlots,
} from './headerModel';
import type { ModelChoice, ModelInfo } from '../types';

const choice = (id: string, input = 0.002, output = 0.01): ModelChoice => ({
  id,
  input_price: input,
  output_price: output,
  context_window: 1000000,
  max_output: 128000,
});

const info: ModelInfo = {
  model: 'claude-sonnet-5',
  light_model: 'claude-haiku-4-5-20251001',
  heavy_model: '',
  chunking_model: 'claude-haiku-4-5',
  qa_model: 'claude-sonnet-5',
};

describe('headerSlots', () => {
  it.each(['basic', 'support', 'review'] as const)(
    'エージェントのタブ（%s）はセレクタ 1 つ・既定は model',
    (tab) => {
      expect(headerSlots(tab, info)).toEqual([
        { slot: tab, label: '利用モデル名：', defaultModel: 'claude-sonnet-5', showHeavy: true },
      ]);
    },
  );

  it('データ管理タブは工程ごとに 2 つ（既定は chunking_model / qa_model）', () => {
    expect(headerSlots('data', info)).toEqual([
      { slot: 'chunking', label: '① チャンキング：', defaultModel: 'claude-haiku-4-5', showHeavy: false },
      { slot: 'qa', label: '② Q/A 作成：', defaultModel: 'claude-sonnet-5', showHeavy: false },
    ]);
  });

  it('既定モデルが未取得なら既定値は空文字（セレクタ自体は出す）', () => {
    expect(headerSlots('data', null).map((s) => s.defaultModel)).toEqual(['', '']);
    expect(headerSlots('basic', null)[0].defaultModel).toBe('');
  });
});

describe('INITIAL_HEADER_MODELS', () => {
  it('初期状態はすべて未選択（= サーバーの既定値）', () => {
    expect(INITIAL_HEADER_MODELS).toEqual({
      basic: '',
      support: '',
      review: '',
      chunking: '',
      qa: '',
    });
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
