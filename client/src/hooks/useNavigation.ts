import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Roles } from '../utils/roles';
import type { Role } from '../utils/roles';

export const useNavigation = () => {
  const navigate = useNavigate();
  const { logoutUser: logout } = useAuth();

  const loginRedirect = (role: Role) => {
    switch (role) {
      case Roles.SUPER_ADMIN:
        navigate('/admin');
        break;
      case Roles.RESTAURANT_ADMIN:
        navigate('/restaurant');
        break;
      case Roles.DRIVER:
        navigate('/driver');
        break;
      case Roles.CUSTOMER:
        navigate('/customer');
        break;
      default:
        navigate('/');
    }
  };

  const logoutAndRedirect = async () => {
    await logout();
    navigate('/login');
  };

  return { loginRedirect, logoutAndRedirect };
};
