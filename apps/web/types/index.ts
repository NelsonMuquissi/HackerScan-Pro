export interface User {
  id: string;
  email: string;
  full_name: string;
}

export interface Workspace {
  id: string;
  name: string;
}

export interface ScanTarget {
  id: string;
  host: string;
  target_type: 'ip' | 'domain' | 'url';
}
