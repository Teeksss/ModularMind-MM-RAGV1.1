import React, { useState, useEffect } from 'react';
import { apiClient } from '../../api/apiClient';
import { User } from '../../contexts/AuthContext';
import { useAuth } from '../../contexts/AuthContext';
import { FiRefreshCw, FiPlus, FiEdit2, FiTrash2, FiCheck, FiX } from 'react-icons/fi';

type UserWithActions = User & {
  isDeleting?: boolean;
  isStatusChanging?: boolean;
};

type FormValues = {
  name: string;
  email: string;
  role: 'admin' | 'user' | 'editor';
  status: 'active' | 'inactive';
  organization?: string;
  password?: string;
};

const UserManagement: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<UserWithActions[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserWithActions | null>(null);
  const [formValues, setFormValues] = useState<FormValues>({
    name: '',
    email: '',
    role: 'user',
    status: 'active',
    organization: '',
    password: ''
  });
  const [notification, setNotification] = useState<{
    show: boolean;
    message: string;
    type: 'success' | 'error';
  }>({
    show: false,
    message: '',
    type: 'success'
  });

  // Load users
  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get<{ users: User[] }>('/api/admin/users');
      setUsers(response.data.users);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError('Failed to load users. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    loadUsers();
  }, []);

  // Show notification
  const showNotification = (message: string, type: 'success' | 'error') => {
    setNotification({
      show: true,
      message,
      type
    });
    
    // Auto hide after 5 seconds
    setTimeout(() => {
      setNotification(prev => ({ ...prev, show: false }));
    }, 5000);
  };

  // Handle form change
  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormValues(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Open modal for adding user
  const handleAddUser = () => {
    setEditingUser(null);
    setFormValues({
      name: '',
      email: '',
      role: 'user',
      status: 'active',
      organization: '',
      password: ''
    });
    setShowModal(true);
  };

  // Open modal for editing user
  const handleEditUser = (user: UserWithActions) => {
    setEditingUser(user);
    setFormValues({
      name: user.name,
      email: user.email,
      role: user.role,
      status: user.status,
      organization: user.organization || '',
      password: '' // Don't set password when editing
    });
    setShowModal(true);
  };

  // Save user (create or update)
  const handleSaveUser = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      
      // Prepare data (remove password if empty)
      const data = { ...formValues };
      if (!data.password) {
        delete data.password;
      }
      
      if (editingUser) {
        // Update existing user
        await apiClient.put(`/api/admin/users/${editingUser.id}`, data);
        showNotification('User updated successfully', 'success');
      } else {
        // Create new user
        await apiClient.post('/api/admin/users', data);
        showNotification('User created successfully', 'success');
      }
      
      // Reload users and close modal
      await loadUsers();
      setShowModal(false);
    } catch (err) {
      console.error('Failed to save user:', err);
      showNotification('Failed to save user', 'error');
    } finally {
      setLoading(false);
    }
  };

  // Delete user
  const handleDeleteUser = async (userId: string) => {
    // Find user and mark as deleting
    setUsers(prev => 
      prev.map(user => 
        user.id === userId ? { ...user, isDeleting: true } : user
      )
    );
    
    try {
      await apiClient.delete(`/api/admin/users/${userId}`);
      showNotification('User deleted successfully', 'success');
      
      // Remove from list
      setUsers(prev => prev.filter(user => user.id !== userId));
    } catch (err) {
      console.error('Failed to delete user:', err);
      showNotification('Failed to delete user', 'error');
      
      // Reset deleting flag
      setUsers(prev => 
        prev.map(user => 
          user.id === userId ? { ...user, isDeleting: false } : user
        )
      );
    }
  };

  // Toggle user status
  const handleToggleStatus = async (userId: string, currentStatus: 'active' | 'inactive') => {
    // Find user and mark as changing status
    setUsers(prev => 
      prev.map(user => 
        user.id === userId ? { ...user, isStatusChanging: true } : user
      )
    );
    
    try {
      const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
      
      await apiClient.patch(`/api/admin/users/${userId}/status`, {
        status: newStatus
      });
      
      showNotification(`User ${newStatus === 'active' ? 'activated' : 'deactivated'} successfully`, 'success');
      
      // Update status in list
      setUsers(prev => 
        prev.map(user => 
          user.id === userId 
            ? { ...user, status: newStatus as 'active' | 'inactive', isStatusChanging: false } 
            : user
        )
      );
    } catch (err) {
      console.error('Failed to update user status:', err);
      showNotification('Failed to update user status', 'error');
      
      // Reset changing status flag
      setUsers(prev => 
        prev.map(user => 
          user.id === userId ? { ...user, isStatusChanging: false } : user
        )
      );
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">User Management</h1>
        
        <div className="flex space-x-2">
          <button
            onClick={loadUsers}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
          >
            <FiRefreshCw className="mr-2" />
            Refresh
          </button>
          
          <button
            onClick={handleAddUser}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
          >
            <FiPlus className="mr-2" />
            Add User
          </button>
        </div>
      </div>
      
      {/* Notification */}
      {notification.show && (
        <div className={`mb-4 p-4 rounded-md ${
          notification.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {notification.message}
          <button
            onClick={() => setNotification(prev => ({ ...prev, show: false }))}
            className="float-right"
          >
            <FiX className="h-5 w-5" />
          </button>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 text-red-800 rounded-md">
          {error}
        </div>
      )}
      
      {/* Users table */}
      <div className="bg-white shadow overflow-hidden border-b border-gray-200 rounded-lg">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Role
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Organization
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {loading && users.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center">
                  <div className="flex justify-center">
                    <svg className="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                </td>
              </tr>
            ) : users.length > 0 ? (
              users.map((user) => (
                <tr key={user.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        {user.avatarUrl ? (
                          <img className="h-10 w-10 rounded-full" src={user.avatarUrl} alt="" />
                        ) : (
                          <div className="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-medium">
                            {user.name.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{user.name}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{user.email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      user.role === 'admin' 
                        ? 'bg-purple-100 text-purple-800' 
                        : user.role === 'editor'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {user.isStatusChanging ? (
                      <svg className="animate-spin h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : (
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        user.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {user.status}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {user.organization || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex justify-end space-x-2">
                      <button
                        onClick={() => handleToggleStatus(user.id, user.status)}
                        disabled={user.id === currentUser?.id || user.isStatusChanging}
                        className={`p-1 rounded-full ${
                          user.status === 'active' 
                            ? 'text-red-600 hover:bg-red-100' 
                            : 'text-green-600 hover:bg-green-100'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                        title={user.status === 'active' ? 'Deactivate' : 'Activate'}
                      >
                        {user.status === 'active' ? <FiX /> : <FiCheck />}
                      </button>
                      
                      <button
                        onClick={() => handleEditUser(user)}
                        className="p-1 text-blue-600 hover:bg-blue-100 rounded-full"
                        title="Edit"
                      >
                        <FiEdit2 />
                      </button>
                      
                      <button
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={user.id === currentUser?.id || user.isDeleting}
                        className="p-1 text-red-600 hover:bg-red-100 rounded-full disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Delete"
                      >
                        {user.isDeleting ? (
                          <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                        ) : (
                          <FiTrash2 />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} className="px-6 py-4 text-center text-sm text-gray-500">
                  No users found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      
      {/* Add/Edit User Modal */}
      {showModal && (
        <div className="fixed z-10 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true">
              <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
            </div>
            
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleSaveUser}>
                <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                  <div className="sm:flex sm:items-start">
                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                      <h3 className="text-lg leading-6 font-medium text-gray-900">
                        {editingUser ? 'Edit User' : 'Add User'}
                      </h3>
                      <div className="mt-4 space-y-4">
                        <div>
                          <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                            Name
                          </label>
                          <input
                            type="text"
                            name="name"
                            id="name"
                            value={formValues.name}
                            onChange={handleFormChange}
                            required
                            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          />
                        </div>
                        
                        <div>
                          <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                            Email
                          </label>
                          <input
                            type="email"
                            name="email"
                            id="email"
                            value={formValues.email}
                            onChange={handleFormChange}
                            required
                            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          />
                        </div>
                        
                        <div>
                          <label htmlFor="role" className="block text-sm font-medium text-gray-700">
                            Role
                          </label>
                          <select
                            id="role"
                            name="role"
                            value={formValues.role}
                            onChange={handleFormChange}
                            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                          >
                            <option value="user">User</option>
                            <option value="editor">Editor</option>
                            <option value="admin">Admin</option>
                          </select>
                        </div>
                        
                        <div>
                          <label htmlFor="status" className="block text-sm font-medium text-gray-700">
                            Status
                          </label>
                          <select
                            id="status"
                            name="status"
                            value={formValues.status}
                            onChange={handleFormChange}
                            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
                          >
                            <option value="active">Active</option>
                            <option value="inactive">Inactive</option>
                          </select>
                        </div>
                        
                        <div>
                          <label htmlFor="organization" className="block text-sm font-medium text-gray-700">
                            Organization
                          </label>
                          <input
                            type="text"
                            name="organization"
                            id="organization"
                            value={formValues.organization || ''}
                            onChange={handleFormChange}
                            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          />
                        </div>
                        
                        <div>
                          <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                            {editingUser ? 'Password (leave blank to keep current)' : 'Password'}
                          </label>
                          <input
                            type="password"
                            name="password"
                            id="password"
                            value={formValues.password || ''}
                            onChange={handleFormChange}
                            required={!editingUser}
                            className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                  <button
                    type="submit"
                    className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                    disabled={loading}
                  >
                    {loading ? (
                      <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                    ) : null}
                    Save
                  </button>
                  <button
                    type="button"
                    className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                    onClick={() => setShowModal(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;