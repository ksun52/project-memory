import { authHandlers } from "./auth";
import { workspaceHandlers } from "./workspace";
import { memorySpaceHandlers } from "./memory-space";
import { sourceHandlers } from "./source";
import { memoryRecordHandlers } from "./memory-record";

export const handlers = [
  ...authHandlers,
  ...workspaceHandlers,
  ...memorySpaceHandlers,
  ...sourceHandlers,
  ...memoryRecordHandlers,
];
