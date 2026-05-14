import { useNavigate } from 'react-router-dom';
import { logout } from '../services/authService';


const Unauthorized = () => {
  const navigate = useNavigate();
  

  const handleGoToLogin = async () => {
    await logout();        // 🔥 clears token + user
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white mb-4">Unauthorized Access</h1>
        <p className="text-gray-300 mb-6">
          You don't have permission to access this page.
        </p>
        <button
          onClick={handleGoToLogin}
          className="px-4 py-2 bg-gold-600 text-white rounded hover:bg-gold-700 transition-colors"
        >
          Go to Login
        </button>
      </div>
    </div>
  );
};

export default Unauthorized;
