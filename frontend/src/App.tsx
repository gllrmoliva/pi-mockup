import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Route, Routes, useNavigate } from 'react-router-dom';

import { AppShell } from './components/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { DeliverablePage } from './pages/DeliverablePage';
import { LoginPage } from './pages/LoginPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ProjectDetailPage } from './pages/ProjectDetailPage';
import { ProjectFormPage } from './pages/ProjectFormPage';
import { ProjectsPage } from './pages/ProjectsPage';
import { SubmissionHistoryPage } from './pages/SubmissionHistoryPage';

export function App() {
    const queryClient = useQueryClient();
    const navigate = useNavigate();

    useEffect(() => {
        function handleSessionExpired() {
            queryClient.clear();
            navigate('/login', { replace: true });
        }

        window.addEventListener('hito:session-expired', handleSessionExpired);
        return () => {
            window.removeEventListener('hito:session-expired', handleSessionExpired);
        };
    }, [navigate, queryClient]);

    return (
        <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
                <Route element={<AppShell />}>
                    <Route index element={<ProjectsPage />} />
                    <Route path="projects/new" element={<ProjectFormPage mode="create" />} />
                    <Route path="projects/:projectId" element={<ProjectDetailPage />} />
                    <Route
                        path="projects/:projectId/edit"
                        element={<ProjectFormPage mode="edit" />}
                    />
                    <Route path="deliverables/:deliverableId" element={<DeliverablePage />} />
                    <Route
                        path="deliverables/:deliverableId/history"
                        element={<SubmissionHistoryPage />}
                    />
                    <Route path="*" element={<NotFoundPage />} />
                </Route>
            </Route>
        </Routes>
    );
}
