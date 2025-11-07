import { createContext, useContext } from 'react';

export const AuthContext = createContext({ me: null, setMe: () => {}, refresh: async () => {}, loading: false });

export const useAuth = () => useContext(AuthContext);


