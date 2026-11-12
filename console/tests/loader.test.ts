import { describe, expect, it } from 'vitest';
import { createHash } from 'node:crypto';
import { loadAll } from '../src/lib/data/loader';
import { read, serve } from './golden';

describe('loadAll', () => {
  it('loads every file of a clean data folder', async () => {
    const loaded = await loadAll('./data/', serve('flat'));
    expect(loaded.status).toBe('ready');
    expect(loaded.invalid).toEqual([]);
    expect(loaded.stale).toEqual([]);
    expect(Object.keys(loaded.missing)).toEqual([]);
    expect(loaded.data.features?.rows).toHaveLength(2);
  });

  it('says there is no data when index.json is missing', async () => {
    const loaded = await loadAll('./data/', serve('flat', { 'index.json': null }));
    expect(loaded.status).toBe('nodata');
  });

  it('refuses a data format it does not read', async () => {
    const index = JSON.parse(read('flat', 'data/index.json'));
    index.formatVersion = 99;
    const loaded = await loadAll('./data/', serve('flat', { 'index.json': JSON.stringify(index) }));
    expect(loaded.status).toBe('outofsync');
    expect(loaded.message).toMatch(/sw-view prepare/);
  });

  it('names the owner of a file that is missing from the index', async () => {
    const index = JSON.parse(read('flat', 'data/index.json'));
    delete index.files['tasks.json'];
    const loaded = await loadAll('./data/', serve('flat', { 'index.json': JSON.stringify(index) }));
    expect(loaded.status).toBe('ready');
    expect(loaded.missing).toEqual({ tasks: 'sw-plan' });
  });

  it('rejects a file whose checksum differs from the index', async () => {
    const loaded = await loadAll('./data/', serve('flat', { 'records.json': read('flat', 'data/records.json') + ' ' }));
    expect(loaded.invalid).toEqual(['records']);
    expect(loaded.data.records).toBeUndefined();
  });

  it('flags a file built from older inputs as stale', async () => {
    const records = JSON.parse(read('flat', 'data/records.json'));
    records.inputsDigest = 'sha256:' + '0'.repeat(64);
    const text = JSON.stringify(records, null, 1) + '\n';
    const index = JSON.parse(read('flat', 'data/index.json'));
    index.files['records.json'].sha256 = 'sha256:' + createHash('sha256').update(text).digest('hex');
    const loaded = await loadAll('./data/', serve('flat', { 'records.json': text, 'index.json': JSON.stringify(index) }));
    expect(loaded.stale).toEqual(['records']);
  });
});
