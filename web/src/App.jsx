import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";

// Pages — imported lazily; will be created in Task 11
// Using placeholder components here so routing is wired and ready
const Login            = () => <div className="p-8 text-xl font-semibold">Login — coming in Task 11</div>;
const Dashboard        = () => <div className="p-8 text-xl font-semibold">Admin Dashboard — coming in Task 11</div>;
const InspectorHome    = () => <div className="p-8 text-xl font-semibold">Inspector Home — coming in Task 11</div>;
const InspectionResult = () => <div className="p-8 text-xl font-semibold">Inspection Result — coming in Task 11</div>;
const InspectionHistory= () => <div className="p-8 text-xl font-semibold">Inspection History — coming in Task 11</div>;
const Products         = () => <div className="p-8 text-xl font-semibold">Products — coming in Task 11</div>;
const Manufacturers    = () => <div className="p-8 text-xl font-semibold">Manufacturers — coming in Task 11</div>;
const Users            = () => <div className="p-8 text-xl font-semibold">Users — coming in Task 11</div>;
const NotFound         = () => <div className="p-8 text-xl font-semibold">404 — Page Not Found</div>;

/**
 * ProtectedRoute — redirects to /login if not authenticated.
 * Optionally enforces a required role (adminOnly).
 */
function ProtectedRoute({ children, adminOnly = false }) {
  const { user, token } = useAuthStore();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && user.role !== "admin") {
    return <Navigate to="/inspector" replace />;
  }

  return children;
}

export default function App() {
  const { user, token } = useAuthStore();

  return (
    <Routes>
      {/* Public */}
      <Route
        path="/login"
        element={
          token ? (
            <Navigate to={user?.role === "admin" ? "/dashboard" : "/inspector"} replace />
          ) : (
            <Login />
          )
        }
      />

      {/* Admin routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute adminOnly>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/products"
        element={
          <ProtectedRoute adminOnly>
            <Products />
          </ProtectedRoute>
        }
      />
      <Route
        path="/manufacturers"
        element={
          <ProtectedRoute adminOnly>
            <Manufacturers />
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute adminOnly>
            <Users />
          </ProtectedRoute>
        }
      />

      {/* Inspector routes */}
      <Route
        path="/inspector"
        element={
          <ProtectedRoute>
            <InspectorHome />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inspections/:id"
        element={
          <ProtectedRoute>
            <InspectionResult />
          </ProtectedRoute>
        }
      />
      <Route
        path="/inspections"
        element={
          <ProtectedRoute>
            <InspectionHistory />
          </ProtectedRoute>
        }
      />

      {/* Default redirect */}
      <Route
        path="/"
        element={
          <Navigate
            to={token ? (user?.role === "admin" ? "/dashboard" : "/inspector") : "/login"}
            replace
          />
        }
      />

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
