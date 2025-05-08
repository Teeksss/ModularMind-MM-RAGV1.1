import React, { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, IconButton,
  Button, Dialog, DialogActions, DialogContent,
  DialogTitle, TextField, MenuItem, Select, FormControl,
  InputLabel, Chip, TablePagination, Tooltip, Snackbar,
  Alert, CircularProgress
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Check as CheckIcon,
  Block as BlockIcon
} from '@mui/icons-material';
import { apiClient } from '../../services/apiClient';
import { useAuth } from '../../contexts/AuthContext';

const UserManagement = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [openDialog, setOpenDialog] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [formValues, setFormValues] = useState({
    name: '',
    email: '',
    role: 'user',
    status: 'active',
    organization: ''
  });
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success'
  });

  // Load users
  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.get('/api/admin/users');
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

  // Handle form change
  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setFormValues({
      ...formValues,
      [name]: value
    });
  };

  // Open dialog for adding user
  const handleOpenAddDialog = () => {
    setEditUser(null);
    setFormValues({
      name: '',
      email: '',
      role: 'user',
      status: 'active',
      organization: ''
    });
    setOpenDialog(true);
  };

  // Open dialog for editing user
  const handleOpenEditDialog = (user) => {
    setEditUser(user);
    setFormValues({
      name: user.name,
      email: user.email,
      role: user.role,
      status: user.status,
      organization: user.organization || ''
    });
    setOpenDialog(true);
  };

  // Close dialog
  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  // Save user (add or edit)
  const handleSaveUser = async () => {
    try {
      setLoading(true);
      
      if (editUser) {
        // Update existing user
        await apiClient.put(`/api/admin/users/${editUser.id}`, formValues);
        setSnackbar({
          open: true,
          message: 'User updated successfully',
          severity: 'success'
        });
      } else {
        // Add new user
        await apiClient.post('/api/admin/users', formValues);
        setSnackbar({
          open: true,
          message: 'User added successfully',
          severity: 'success'
        });
      }
      
      // Reload users
      await loadUsers();
      handleCloseDialog();
    } catch (err) {
      console.error('Failed to save user:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.message || 'Failed to save user',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Delete user
  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) {
      return;
    }
    
    try {
      setLoading(true);
      
      await apiClient.delete(`/api/admin/users/${userId}`);
      
      setSnackbar({
        open: true,
        message: 'User deleted successfully',
        severity: 'success'
      });
      
      // Reload users
      await loadUsers();
    } catch (err) {
      console.error('Failed to delete user:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.message || 'Failed to delete user',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Toggle user status
  const handleToggleStatus = async (userId, currentStatus) => {
    try {
      setLoading(true);
      
      const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
      
      await apiClient.patch(`/api/admin/users/${userId}/status`, {
        status: newStatus
      });
      
      setSnackbar({
        open: true,
        message: `User ${newStatus === 'active' ? 'activated' : 'deactivated'} successfully`,
        severity: 'success'
      });
      
      // Reload users
      await loadUsers();
    } catch (err) {
      console.error('Failed to update user status:', err);
      setSnackbar({
        open: true,
        message: err.response?.data?.message || 'Failed to update user status',
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle page change
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  // Handle rows per page change
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // Close snackbar
  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  // Calculate pagination
  const paginatedUsers = users.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5">User Management</Typography>
        
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadUsers}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenAddDialog}
          >
            Add User
          </Button>
        </Box>
      </Box>
      
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}
      
      <Paper elevation={0} variant="outlined">
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Organization</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading && users.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    <CircularProgress size={24} sx={{ my: 2 }} />
                  </TableCell>
                </TableRow>
              ) : paginatedUsers.length > 0 ? (
                paginatedUsers.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>{user.name}</TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <Chip
                        label={user.role}
                        color={user.role === 'admin' ? 'primary' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.status}
                        color={user.status === 'active' ? 'success' : 'error'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{user.organization || '-'}</TableCell>
                    <TableCell align="right">
                      <Tooltip title={user.status === 'active' ? 'Deactivate' : 'Activate'}>
                        <IconButton
                          color={user.status === 'active' ? 'error' : 'success'}
                          onClick={() => handleToggleStatus(user.id, user.status)}
                          disabled={user.id === currentUser?.id}
                          size="small"
                        >
                          {user.status === 'active' ? <BlockIcon /> : <CheckIcon />}
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Edit">
                        <IconButton
                          color="primary"
                          onClick={() => handleOpenEditDialog(user)}
                          size="small"
                        >
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      
                      <Tooltip title="Delete">
                        <IconButton
                          color="error"
                          onClick={() => handleDeleteUser(user.id)}
                          disabled={user.id === currentUser?.id}
                          size="small"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} align="center">
                    No users found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={users.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      </Paper>
      
      {/* Add/Edit User Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editUser ? 'Edit User' : 'Add User'}
        </DialogTitle>
        
        <DialogContent dividers>
          <Box component="form" sx={{ '& .MuiTextField-root': { mb: 2 } }}>
            <TextField
              label="Name"
              name="name"
              value={formValues.name}
              onChange={handleFormChange}
              fullWidth
              required
            />
            
            <TextField
              label="Email"
              name="email"
              type="email"
              value={formValues.email}
              onChange={handleFormChange}
              fullWidth
              required
            />
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Role</InputLabel>
              <Select
                name="role"
                value={formValues.role}
                onChange={handleFormChange}
                label="Role"
              >
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
                <MenuItem value="editor">Editor</MenuItem>
              </Select>
            </FormControl>
            
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Status</InputLabel>
              <Select
                name="status"
                value={formValues.status}
                onChange={handleFormChange}
                label="Status"
              >
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="inactive">Inactive</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              label="Organization"
              name="organization"
              value={formValues.organization}
              onChange={handleFormChange}
              fullWidth
            />
          </Box>
        </DialogContent>
        
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            onClick={handleSaveUser}
            variant="contained"
            disabled={loading}
          >
            {loading ? <CircularProgress size={24} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default UserManagement;