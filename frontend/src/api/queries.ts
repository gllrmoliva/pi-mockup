import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as api from './client';
import type { DeliverableInput, MilestoneInput, ProjectInput, ReviewDecision } from './types';

export const queryKeys = {
    me: ['me'] as const,
    projects: ['projects'] as const,
    pendingReviews: ['pending-reviews'] as const,
    project: (projectId: string) => ['project', projectId] as const,
    deliverable: (deliverableId: string) => ['deliverable', deliverableId] as const,
    history: (deliverableId: string) => ['deliverable', deliverableId, 'submissions'] as const,
};

function invalidateProjectData(queryClient: ReturnType<typeof useQueryClient>): void {
    void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    void queryClient.invalidateQueries({ queryKey: ['project'] });
    void queryClient.invalidateQueries({ queryKey: queryKeys.pendingReviews });
}

export function useMe() {
    return useQuery({
        queryKey: queryKeys.me,
        queryFn: api.getMe,
        retry: false,
    });
}

export function useProjects() {
    return useQuery({
        queryKey: queryKeys.projects,
        queryFn: api.getProjects,
    });
}

export function usePendingReviews() {
    return useQuery({
        queryKey: queryKeys.pendingReviews,
        queryFn: api.getPendingReviews,
    });
}

export function useProject(projectId: string | undefined) {
    return useQuery({
        queryKey: queryKeys.project(projectId ?? ''),
        queryFn: () => api.getProject(projectId ?? ''),
        enabled: Boolean(projectId),
    });
}

export function useDeliverable(deliverableId: string | undefined) {
    return useQuery({
        queryKey: queryKeys.deliverable(deliverableId ?? ''),
        queryFn: () => api.getDeliverable(deliverableId ?? ''),
        enabled: Boolean(deliverableId),
    });
}

export function useSubmissionHistory(deliverableId: string | undefined) {
    return useQuery({
        queryKey: queryKeys.history(deliverableId ?? ''),
        queryFn: () => api.getSubmissions(deliverableId ?? ''),
        enabled: Boolean(deliverableId),
    });
}

export function useLogin() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ email, password }: { email: string; password: string }) =>
            api.login(email, password),
        onSuccess: (user) => {
            queryClient.setQueryData(queryKeys.me, user);
            void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
            void queryClient.invalidateQueries({
                queryKey: queryKeys.pendingReviews,
            });
        },
    });
}

export function useLogout() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: api.logout,
        onSuccess: () => {
            queryClient.clear();
        },
    });
}

export function useCreateProject() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (input: ProjectInput) => api.createProject(input),
        onSuccess: () => {
            invalidateProjectData(queryClient);
        },
    });
}

export function useUpdateProject() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ projectId, input }: { projectId: string; input: ProjectInput }) =>
            api.updateProject(projectId, input),
        onSuccess: () => {
            invalidateProjectData(queryClient);
        },
    });
}

export function useCreateMilestone() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ projectId, input }: { projectId: string; input: MilestoneInput }) =>
            api.createMilestone(projectId, input),
        onSuccess: () => {
            invalidateProjectData(queryClient);
        },
    });
}

export function useCreateDeliverable() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ milestoneId, input }: { milestoneId: string; input: DeliverableInput }) =>
            api.createDeliverable(milestoneId, input),
        onSuccess: () => {
            invalidateProjectData(queryClient);
        },
    });
}

export function useUpdateDeliverable() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            deliverableId,
            input,
        }: {
            deliverableId: string;
            input: DeliverableInput;
        }) => api.updateDeliverable(deliverableId, input),
        onSuccess: (_data, variables) => {
            void queryClient.invalidateQueries({
                queryKey: queryKeys.deliverable(variables.deliverableId),
            });
            invalidateProjectData(queryClient);
        },
    });
}

export function useSubmitDeliverable() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            deliverableId,
            files,
            linkUrl,
        }: {
            deliverableId: string;
            files: File[];
            linkUrl: string;
        }) => api.submitDeliverable(deliverableId, files, linkUrl),
        onSuccess: (_data, variables) => {
            void queryClient.invalidateQueries({
                queryKey: queryKeys.deliverable(variables.deliverableId),
            });
            void queryClient.invalidateQueries({
                queryKey: queryKeys.history(variables.deliverableId),
            });
            invalidateProjectData(queryClient);
        },
    });
}

export function useReviewDeliverable() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({
            deliverableId,
            decision,
        }: {
            deliverableId: string;
            decision: ReviewDecision;
        }) => api.reviewDeliverable(deliverableId, decision),
        onSuccess: (_data, variables) => {
            void queryClient.invalidateQueries({
                queryKey: queryKeys.deliverable(variables.deliverableId),
            });
            void queryClient.invalidateQueries({
                queryKey: queryKeys.history(variables.deliverableId),
            });
            invalidateProjectData(queryClient);
        },
    });
}

export function usePostMessage() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ deliverableId, body }: { deliverableId: string; body: string }) =>
            api.postMessage(deliverableId, body),
        onSuccess: (_data, variables) => {
            void queryClient.invalidateQueries({
                queryKey: queryKeys.deliverable(variables.deliverableId),
            });
            invalidateProjectData(queryClient);
        },
    });
}
