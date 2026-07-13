import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ToastProvider } from "./components/Toaster";
import { Layout } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ClaimsListPage } from "./pages/ClaimsListPage";
import { NewClaimPage } from "./pages/NewClaimPage";
import { ClaimDetailPage } from "./pages/ClaimDetailPage";
import { ReviewQueuePage } from "./pages/ReviewQueuePage";
import { AdminPoliciesPage } from "./pages/AdminPoliciesPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AdminEvaluationPage } from "./pages/AdminEvaluationPage";
import { AdminAuditLogPage } from "./pages/AdminAuditLogPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import type { UserRole } from "./api/types";
import type { ReactNode } from "react";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireRole({ roles, children }: { roles: UserRole[]; children: ReactNode }) {
  const { user } = useAuth();
  if (!user) return null;
  if (!roles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function HomeRedirect() {
  const { user } = useAuth();
  if (!user) return null;
  if (user.role === "customer") return <Navigate to="/claims" replace />;
  if (user.role === "adjuster") return <Navigate to="/review" replace />;
  return <Navigate to="/admin/policies" replace />;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/notifications" element={<NotificationsPage />} />

        <Route
          path="/claims"
          element={
            <RequireRole roles={["customer"]}>
              <ClaimsListPage />
            </RequireRole>
          }
        />
        <Route
          path="/claims/new"
          element={
            <RequireRole roles={["customer"]}>
              <NewClaimPage />
            </RequireRole>
          }
        />
        <Route path="/claims/:id" element={<ClaimDetailPage />} />

        <Route
          path="/review"
          element={
            <RequireRole roles={["adjuster", "admin"]}>
              <ReviewQueuePage />
            </RequireRole>
          }
        />

        <Route
          path="/admin/policies"
          element={
            <RequireRole roles={["admin"]}>
              <AdminPoliciesPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/users"
          element={
            <RequireRole roles={["admin"]}>
              <AdminUsersPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/evaluation"
          element={
            <RequireRole roles={["admin"]}>
              <AdminEvaluationPage />
            </RequireRole>
          }
        />
        <Route
          path="/admin/audit-log"
          element={
            <RequireRole roles={["admin"]}>
              <AdminAuditLogPage />
            </RequireRole>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ToastProvider>
  );
}
