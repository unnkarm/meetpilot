import { createContext, useContext } from 'react';

export const isWorkspaceManager = (role?: string) => role === 'owner' || role === 'admin';
export const WorkspaceManagerContext = createContext(false);
export const useWorkspaceManager = () => useContext(WorkspaceManagerContext);
