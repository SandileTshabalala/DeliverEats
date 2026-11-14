import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./ProtectedRoute";
import Login from "./auth/Login";
import Register from "./auth/Register";
import { ForgotPassword, ResetPassword } from "./auth/PasswordReset";
import Landing from "./pages/Landing";
import { Roles } from "./utils/roles";
import { useAuth } from "./context/AuthContext";

const AdminLayout = lazy(() => import("./layouts/AdminLayout"));
const RestaurantLayout = lazy(() => import("./layouts/RestaurantLayout"));
const DriverLayout = lazy(() => import("./layouts/DriverLayout"));
const CustomerLayout = lazy(() => import("./layouts/CustomerLayout"));
const Unauthorized = lazy(() => import("./pages/Unauthorized"));
const NotFound = lazy(() => import("./pages/NotFound"));
const CustomerPaymentResult = lazy(() => import("./pages/customer/PaymentResult"));
const RestaurantPaymentResult = lazy(() => import("./pages/restaurant/PaymentResult"));
const Privacy = lazy(() => import("./pages/legal/Privacy"));
const Terms = lazy(() => import("./pages/legal/Terms"));
const Dashboard = lazy(() => import("./pages/admin/Dashboard"));
const Users = lazy(() => import("./pages/admin/Users"));
const PaymentSettings = lazy(() => import("./pages/admin/PaymentSettings"));
const AdminBilling = lazy(() => import("./pages/admin/Billing"));
const AdminRestaurants = lazy(() => import("./pages/admin/Restaurants"));
const AdminSettings = lazy(() => import("./pages/admin/Settings"));
const AdminReports = lazy(() => import("./pages/admin/Reports"));
const AdminCategories = lazy(() => import("./pages/admin/Categories"));
const RestaurantDashboard = lazy(() => import("./pages/restaurant/Dashboard"));
const RestaurantOrders = lazy(() => import("./pages/restaurant/Orders"));
const RestaurantMenus = lazy(() => import("./pages/restaurant/Menus"));
const RestaurantSettings = lazy(() => import("./pages/restaurant/Settings"));
const RestaurantTeam = lazy(() => import("./pages/restaurant/Team"));
const RestaurantReports = lazy(() => import("./pages/restaurant/Reports"));
const DriverDashboard = lazy(() => import("./pages/driver/Dashboard"));
const DriverJobs = lazy(() => import("./pages/driver/Jobs"));
const DriverSettings = lazy(() => import("./pages/driver/Settings"));
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
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/unauthorized" element={<Unauthorized />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />

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
        <Route path="billing" element={<AdminBilling />} />
        <Route path="categories" element={<AdminCategories />} />
        <Route path="restaurants" element={<AdminRestaurants />} />
        <Route path="reports" element={<AdminReports />} />
        <Route path="settings" element={<AdminSettings />} />
        <Route path="*" element={<NotFound home="/admin/dashboard" embedded />} />
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
        <Route path="team" element={<RestaurantTeam />} />
        <Route path="reports" element={<RestaurantReports />} />
        <Route path="settings" element={<RestaurantSettings />} />
        <Route path="payment" element={<RestaurantPaymentResult />} />
        <Route path="*" element={<NotFound home="/restaurant/dashboard" embedded />} />
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
        <Route path="settings" element={<DriverSettings />} />
        <Route path="*" element={<NotFound home="/driver/dashboard" embedded />} />
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
        <Route path="payment" element={<CustomerPaymentResult />} />
        <Route path="*" element={<NotFound home="/customer" embedded />} />
      </Route>

      {/* FALLBACK */}
      <Route path="*" element={<NotFound />} />
    </Routes>
    </Suspense>
  );
}
