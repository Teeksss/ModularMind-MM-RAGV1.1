import { useEffect, useState } from 'react';

// Custom hook for responsive design
export const useResponsive = () => {
  const [windowSize, setWindowSize] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  });
  
  // Screen size breakpoints (matching Tailwind's defaults)
  const breakpoints = {
    sm: 640,
    md: 768,
    lg: 1024,
    xl: 1280,
    '2xl': 1536,
  };
  
  useEffect(() => {
    // Handler to call on window resize
    const handleResize = () => {
      setWindowSize({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };
    
    // Add event listener
    window.addEventListener('resize', handleResize);
    
    // Call handler right away so state gets updated with initial window size
    handleResize();
    
    // Remove event listener on cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
  return {
    width: windowSize.width,
    height: windowSize.height,
    isPortrait: windowSize.height > windowSize.width,
    isLandscape: windowSize.width > windowSize.height,
    isMobile: windowSize.width < breakpoints.md,
    isTablet: windowSize.width >= breakpoints.md && windowSize.width < breakpoints.lg,
    isDesktop: windowSize.width >= breakpoints.lg,
    isLargeDesktop: windowSize.width >= breakpoints.xl,
    breakpoints,
  };
};

// Helper function to get appropriate responsive value based on screen size
export const getResponsiveValue = <T,>(
  values: { mobile?: T; tablet?: T; desktop?: T; default: T },
  screenWidth: number
): T => {
  const { breakpoints } = useResponsive();
  
  if (screenWidth < breakpoints.md && values.mobile !== undefined) {
    return values.mobile;
  }
  
  if (screenWidth < breakpoints.lg && values.tablet !== undefined) {
    return values.tablet;
  }
  
  if (screenWidth >= breakpoints.lg && values.desktop !== undefined) {
    return values.desktop;
  }
  
  return values.default;
};

// Detect touch device
export const isTouchDevice = (): boolean => {
  if (typeof window === 'undefined') return false;
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
};