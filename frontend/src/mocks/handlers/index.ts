import { authHandlers } from "./auth";
import { workspaceHandlers } from "./workspace";
import { memorySpaceHandlers } from "./memory-space";

export const handlers = [
  ...authHandlers,
  ...workspaceHandlers,
  ...memorySpaceHandlers,
];
