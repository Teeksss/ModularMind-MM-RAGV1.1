import React, { useState } from 'react';
import {
  AppBar, Toolbar, IconButton, Typography, Button,
  Drawer, List, ListItem, ListItemIcon, ListItemText,
  Box, useMediaQuery, useTheme, Divider, Avatar
} from '@mui/material';
import {
  Menu as MenuIcon,
  Search as SearchIcon,
  Upload as UploadIcon,
  Settings as SettingsIcon,
  Dashboard as DashboardIcon,
  Person as PersonIcon,
  ChevronLeft as ChevronLeftIcon,
  Logout as LogoutIcon
} from '@mui/icons-material';
import { Link, useLocation } from 'react-router-dom';
import { styled } from '@mui/material/styles';

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  zIndex: theme.zIndex.drawer + 1,
}));

const ResponsiveAppBar = ({ user }) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const location = useLocation();

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Search', icon: <SearchIcon />, path: '/search' },
    { text: 'Upload Documents', icon: <UploadIcon />, path: '/upload' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ];

  const isActive = (path) => {
    return location.pathname.startsWith(path);
  };

  const drawer = (
    <>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          p: 1,
        }}
      >
        <IconButton onClick={handleDrawerToggle}>
          <ChevronLeftIcon />
        </IconButton>
      </Box>
      <Divider />
      <List>
        {menuItems.map((item) => (
          <ListItem
            button
            key={item.text}
            component={Link}
            to={item.path}
            selected={isActive(item.path)}
            onClick={isMobile ? handleDrawerToggle : undefined}
            sx={{
              bgcolor: isActive(item.path) ? 'action.selected' : 'transparent',
              '&:hover': {
                bgcolor: 'action.hover',
              },
            }}
          >
            <ListItemIcon
              sx={{
                color: isActive(item.path) ? 'primary.main' : 'inherit',
              }}
            >
              {item.icon}
            </ListItemIcon>
            <ListItemText
              primary={item.text}
              primaryTypographyProps={{
                color: isActive(item.path) ? 'primary.main' : 'inherit',
                fontWeight: isActive(item.path) ? 500 : 400,
              }}
            />
          </ListItem>
        ))}
      </List>
      
      <Divider sx={{ mt: 'auto' }} />
      
      {user && (
        <Box sx={{ p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <Avatar
              src={user.avatarUrl}
              alt={user.name}
              sx={{ width: 32, height: 32, mr: 1 }}
            />
            <Box>
              <Typography variant="body2" fontWeight={500}>
                {user.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {user.email}
              </Typography>
            </Box>
          </Box>
          
          <Button
            variant="outlined"
            color="inherit"
            startIcon={<LogoutIcon />}
            fullWidth
            size="small"
          >
            Logout
          </Button>
        </Box>
      )}
    </>
  );

  return (
    <>
      <StyledAppBar position="fixed" color="default" elevation={1}>
        <Toolbar>
          {isMobile && (
            <IconButton
              color="inherit"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}
          
          <Typography
            variant="h6"
            noWrap
            component={Link}
            to="/"
            sx={{
              color: 'inherit',
              textDecoration: 'none',
              flexGrow: 1,
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <img
              src="/logo.svg"
              alt="ModularMind Logo"
              style={{ height: 32, marginRight: 8 }}
            />
            ModularMind
          </Typography>
          
          {!isMobile && (
            <Box sx={{ display: 'flex' }}>
              {menuItems.map((item) => (
                <Button
                  key={item.text}
                  component={Link}
                  to={item.path}
                  color={isActive(item.path) ? 'primary' : 'inherit'}
                  sx={{ 
                    mx: 1,
                    fontWeight: isActive(item.path) ? 500 : 400,
                  }}
                  startIcon={item.icon}
                >
                  {item.text}
                </Button>
              ))}
            </Box>
          )}
          
          {!isMobile && user && (
            <Box sx={{ display: 'flex', alignItems: 'center', ml: 2 }}>
              <IconButton
                component={Link}
                to="/profile"
                sx={{ ml: 1 }}
              >
                <Avatar
                  src={user.avatarUrl}
                  alt={user.name}
                  sx={{ width: 32, height: 32 }}
                />
              </IconButton>
            </Box>
          )}
        </Toolbar>
      </StyledAppBar>
      
      <Drawer
        variant={isMobile ? "temporary" : "permanent"}
        open={isMobile ? drawerOpen : true}
        onClose={isMobile ? handleDrawerToggle : undefined}
        sx={{
          width: 240,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: 240,
            boxSizing: 'border-box',
          },
        }}
      >
        {drawer}
      </Drawer>
      
      {/* Toolbar spacer to push content below app bar */}
      <Toolbar />
    </>
  );
};

export default ResponsiveAppBar;