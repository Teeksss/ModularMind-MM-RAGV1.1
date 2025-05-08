import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });
  
  test('should show login form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Sign in to your account' })).toBeVisible();
    await expect(page.getByLabel('Email address')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible();
  });
  
  test('should display error with invalid credentials', async ({ page }) => {
    await page.getByLabel('Email address').fill('invalid@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: 'Sign in' }).click();
    
    await expect(page.getByText('Invalid email or password')).toBeVisible();
  });
  
  test('should login successfully with valid credentials', async ({ page }) => {
    await page.getByLabel('Email address').fill('admin@example.com');
    await page.getByLabel('Password').fill('password123');
    await page.getByRole('button', { name: 'Sign in' }).click();
    
    // Wait for navigation to dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByText('Welcome back')).toBeVisible();
  });
  
  test('should allow registration', async ({ page }) => {
    // Navigate to register page
    await page.getByText('Create an account').click();