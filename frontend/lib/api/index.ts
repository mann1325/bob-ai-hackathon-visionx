import { ApiClient } from './client';
import { MockAdapter } from './mock-adapter';
import { RealAdapter } from './real-adapter';

// Default to MockAdapter out of the box if no flag is provided, or strictly follow flag if provided
const useMocks = process.env.NEXT_PUBLIC_USE_MOCKS !== 'false';

const apiClient: ApiClient = useMocks ? new MockAdapter() : new RealAdapter();

export default apiClient;
