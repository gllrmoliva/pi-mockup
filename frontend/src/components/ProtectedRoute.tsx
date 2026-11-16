import { Navigate, Outlet } from 'react-router-dom';

import { useMe } from '../api/queries';
import { LoadingState } from './LoadingState';

export function ProtectedRoute() {
    const me = useMe();

    if (me.isPending) {
        return <LoadingState label="Cargando sesión…" />;
    }

    if (me.isError || !me.data) {
        return <Navigate to="/login" replace />;
    }

    return <Outlet />;
}
