import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiClient } from '../../api/apiClient';
import { User } from '../../types/user';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('authToken'),
  loading: false,
  error: null,
  isAuthenticated: !!localStorage.getItem('authToken'),
};

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async ({ email, password }: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await apiClient.post<{ token: string; user: User }>('/api/auth/login', { 
        email, 
        password 
      });
      
      // Store token in localStorage
      localStorage.setItem('authToken', response.data.token);
      
      // Set auth token for future requests
      apiClient.setAuthToken(response.data.token);
      
      return response.data;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.error?.message || 'Login failed'
      );
    }
  }
);

export const register = createAsyncThunk(
  'auth/register',
  async (userData: { name: string; email: string; password: string; organization?: string }, { rejectWithValue }) => {
    try {
      const response = await apiClient.post<{ token: string; user: User }>('/api/auth/register', userData);
      
      // Store token in localStorage
      localStorage.setItem('authToken', response.data.token);
      
      // Set auth token for future requests
      apiClient.setAuthToken(response.data.token);
      
      return response.data;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.error?.message || 'Registration failed'
      );
    }
  }
);

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      // Call logout endpoint
      await apiClient.post('/api/auth/logout');
      
      // Clear localStorage
      localStorage.removeItem('authToken');
      
      // Clear auth token from API client
      apiClient.clearAuthToken();
      
      return true;
    } catch (error: any) {
      // Even if the API call fails, we want to clear local state
      localStorage.removeItem('authToken');
      apiClient.clearAuthToken();
      
      return rejectWithValue(
        error.response?.data?.error?.message || 'Logout failed'
      );
    }
  }
);

export const fetchCurrentUser = createAsyncThunk(
  'auth/fetchCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get<{ user: User }>('/api/auth/me');
      return response.data.user;
    } catch (error: any) {
      // If unauthorized, clear token
      if (error.response?.status === 401) {
        localStorage.removeItem('authToken');
        apiClient.clearAuthToken();
      }
      
      return rejectWithValue(
        error.response?.data?.error?.message || 'Failed to fetch user data'
      );
    }
  }
);

export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (profileData: Partial<User>, { rejectWithValue }) => {
    try {
      const response = await apiClient.put<{ user: User }>('/api/auth/profile', profileData);
      return response.data.user;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.error?.message || 'Failed to update profile'
      );
    }
  }
);

// Create the slice
const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    resetError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Login
    builder.addCase(login.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(login.fulfilled, (state, action) => {
      state.loading = false;
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.isAuthenticated = true;
    });
    builder.addCase(login.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
      state.isAuthenticated = false;
    });
    
    // Register
    builder.addCase(register.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(register.fulfilled, (state, action) => {
      state.loading = false;
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.isAuthenticated = true;
    });
    builder.addCase(register.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
      state.isAuthenticated = false;
    });
    
    // Logout
    builder.addCase(logout.pending, (state) => {
      state.loading = true;
    });
    builder.addCase(logout.fulfilled, (state) => {
      state.loading = false;
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = null;
    });
    builder.addCase(logout.rejected, (state) => {
      state.loading = false;
      state.user = null;
      state.token = null;
      state.isAuthenticated = false;
      state.error = null;
    });
    
    // Fetch current user
    builder.addCase(fetchCurrentUser.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(fetchCurrentUser.fulfilled, (state, action) => {
      state.loading = false;
      state.user = action.payload;
      state.isAuthenticated = true;
    });
    builder.addCase(fetchCurrentUser.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
      state.isAuthenticated = false;
      state.user = null;
      state.token = null;
    });
    
    // Update profile
    builder.addCase(updateProfile.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(updateProfile.fulfilled, (state, action) => {
      state.loading = false;
      state.user = action.payload;
    });
    builder.addCase(updateProfile.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });
  },
});

export const { resetError } = authSlice.actions;

export default authSlice.reducer;