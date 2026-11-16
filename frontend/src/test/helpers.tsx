import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import { App } from '../App';

export function jsonResponse(body: unknown, status = 200): Response {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
    } as Response;
}

export function createQueryClient(): QueryClient {
    return new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });
}

export function renderApp(initialPath = '/') {
    return render(
        <QueryClientProvider client={createQueryClient()}>
            <MemoryRouter initialEntries={[initialPath]}>
                <App />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

type FetchHandler = (url: string, init?: RequestInit) => Response | Promise<Response>;

export function stubFetch(handler: FetchHandler) {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
        Promise.resolve(handler(String(input), init)),
    );
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
}
