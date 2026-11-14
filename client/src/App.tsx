import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import AppRouter from './router';
import { Toaster } from 'react-hot-toast';

// Layout component to handle auth state
const AppContent = () => {
  return (
    <Routes>
      <Route path="/*" element={<AppRouter />} />
    </Routes>
  );
};

import { CartProvider } from './context/CartContext';

function App() {
  return (
    <ThemeProvider>
    <AuthProvider>
      <CartProvider>
        <Router>
          <AppContent />
          <Toaster position="top-right" />
        </Router>
      </CartProvider>
    </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
