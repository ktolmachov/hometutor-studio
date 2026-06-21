import { expect, test as base } from '@playwright/test';

type WorkerDbFixtures = {
  workerDbPath: string;
};

export const test = base.extend<WorkerDbFixtures>({
  workerDbPath: [
    async ({}, use, testInfo) => {
      const idx = testInfo.workerIndex;
      const dbPath =
        process.env[`USER_STATE_DB_${idx}`] ??
        process.env.USER_STATE_DB ??
        '.e2e/state-main.db';
      await use(dbPath);
    },
    { scope: 'worker' },
  ],
});

export { expect };
