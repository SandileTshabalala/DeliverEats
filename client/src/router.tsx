import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import Login from "./auth/Login";
import Register from "./auth/Register";
import Landing from "./pages/Landing";
import { Roles } from "./utils/roles";
import { useAuth } from "./context/AuthContext";

const AdminLayout = lazy(() => import("./layouts/AdminLayout"));
const RestaurantLayout = lazy(() => import("./layouts/RestaurantLayout"));
const DriverLayout = lazy(() => import("./layouts/DriverLayout"));
const CustomerLayout = lazy(() => import("./layouts/CustomerLayout"));
const Unauthorized = lazy(() => import("./pages/Unauthorized"));
const Dashboard = lazy(() => import("./pages/admin/Dashboard"));
const Users = lazy(() => import("./pages/admin/Users"));
const PaymentSettings = lazy(() => import("./pages/admin/PaymentSettings"));
const RestaurantDashboard = lazy(() => import("./pages/restaurant/Dashboard"));
const RestaurantOrders = lazy(() => import("./pages/restaurant/Orders"));
const RestaurantMenus = lazy(() => import("./pages/restaurant/Menus"));
const DriverDashboard = lazy(() => import("./pages/driver/Dashboard"));
const DriverJobs = lazy(() => import("./pages/driver/Jobs"));
const CustomerDashboard = lazy(() => import("./pages/customer/Dashboard"));
const CustomerMenu = lazy(() => import("./pages/customer/Menu"));
const CustomerCart = lazy(() => import("./pages/customer/Cart"));
const CustomerOrders = lazy(() => import("./pages/customer/Orders"));
const CustomerRestaurants = lazy(() => import("./pages/customer/Restaurants"));
const CustomerProfile = lazy(() => import("./pages/customer/Profile"));

const PageLoader = () => (
  <div className="min-h-screen bg-gray-900 flex items-center justify-center">
    <div className="text-white">Loading...</div>
  </div>
);

export default function AppRouter() {
  const { user } = useAuth();

  return (
    <Suspense fallback={<PageLoader />}>
    <Routes>
      {/* PUBLIC ROUTES */}
      <Route
        path="/"
        element={
          user ? (
            (user.role === Roles.SUPER_ADMIN || user.role === Roles.ADMIN) ? <Navigate to="/admin" replace /> :
              user.role === Roles.RESTAURANT_ADMIN ? <Navigate to="/restaurant" replace /> :
                user.role === Roles.DRIVER ? <Navigate to="/driver" replace /> :
                  <Navigate to="/customer" replace />
          ) : <Landing />
        }
      />

      <Route
        path="/login"
        element={
          user ? (
            (user.role === Roles.SUPER_ADMIN || user.role === Roles.ADMIN) ? <Navigate to="/admin" replace /> :
              user.role === Roles.RESTAURANT_ADMIN ? <Navigate to="/restaurant" replace /> :
                user.role === Roles.DRIVER ? <Navigate to="/driver" replace /> :
                  <Navigate to="/customer" replace />
          ) : <Login />
        }
      />

      <Route path="/register" element={<Register />} />
      <Route path="/unauthorized" element={<Unauthorized />} />

      {/* PROTECTED ROUTES */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute roles={[Roles.SUPER_ADMIN, Roles.ADMIN]}>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="users" element={<Users />} />
        <Route path="payments" element={<PaymentSettings />} />
        <Route path="*" element={<div className="p-8 text-center text-gray-500">Coming Soon</div>} />
      </Route>

      <Route
        path="/restaurant"
        element={
          <ProtectedRoute roles={[Roles.RESTAURANT_ADMIN]}>
            <RestaurantLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<RestaurantDashboard />} />
        <Route path="orders" element={<RestaurantOrders />} />
        <Route path="menus" element={<RestaurantMenus />} />
        <Route path="*" element={<div className="p-8 text-center text-gray-500 uppercase tracking-widest font-black">Coming Soon</div>} />
      </Route>

      <Route
        path="/driver"
        element={
          <ProtectedRoute roles={[Roles.DRIVER]}>
            <DriverLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<DriverDashboard />} />
        <Route path="jobs" element={<DriverJobs />} />
        <Route path="*" element={<div className="p-8 text-center text-gray-500 uppercase tracking-widest font-black">Coming Soon</div>} />
      </Route>

      <Route
        path="/customer"
        element={
          <ProtectedRoute roles={[Roles.CUSTOMER]}>
            <CustomerLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<CustomerDashboard />} />
        <Route path="restaurants" element={<CustomerRestaurants />} />
        <Route path="menu/:restaurantId" element={<CustomerMenu />} />
        <Route path="cart" element={<CustomerCart />} />
        <Route path="profile" element={<CustomerProfile />} />
        <Route path="orders" element={<CustomerOrders />} />
        <Route path="*" element={<Navigate to="/customer" replace />} />
      </Route>

      {/* FALLBACK */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  );
}
