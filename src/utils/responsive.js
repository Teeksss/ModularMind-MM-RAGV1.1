import { useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';

export const useResponsive = () => {
  const theme = useTheme();
  
  return {
    isMobile: useMediaQuery(theme.breakpoints.down('sm')),
    isTablet: useMediaQuery(theme.breakpoints.between('sm', 'md')),
    isDesktop: useMediaQuery(theme.breakpoints.up('md')),
    isLargeDesktop: useMediaQuery(theme.breakpoints.up('lg')),
    
    // Orientation
    isPortrait: useMediaQuery('(orientation: portrait)'),
    isLandscape: useMediaQuery('(orientation: landscape)'),
    
    // Visibility helpers
    showOnMobile: { display: { xs: 'block', sm: 'none' } },
    hideOnMobile: { display: { xs: 'none', sm: 'block' } },
    showOnTablet: { display: { xs: 'none', sm: 'block', md: 'none' } },
    hideOnTablet: { display: { xs: 'block', sm: 'none', md: 'block' } },
    showOnDesktop: { display: { xs: 'none', md: 'block' } },
    hideOnDesktop: { display: { xs: 'block', md: 'none' } },
  };
};