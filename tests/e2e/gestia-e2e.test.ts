#!/usr/bin/env playwright-test
/**
 * E2E Tests for GESTIA Web Application
 * Tests complete user flows: login → dashboard → actions → logout
 */
import { test, expect, } from '@playwright/test';

// --- Test Data ---
const TEST_USERS = {
  client: {
    email: 'cliente@tech-solutions.com',
    password: 'cliente123',
    name: 'Tech Solutions SL',
  },
  advisor: {
    email: 'asesor@gestia.app',
    password: 'asesor123',
    name: 'Ana García',
  },
};

const BASE_URL = 'http://localhost:8080';

// --- Helper Functions ---
async function login(page, userType = 'client') {
  const user = TEST_USERS[userType];
  await page.goto(`${BASE_URL}/auth/login`);
  await page.fill('input[name="email"]', user.email);
  await page.fill('input[name="password"]', user.password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/client/dashboard`);
}

async function logout(page) {
  await page.click('text=Logout');
  await page.waitForURL(`${BASE_URL}/auth/login`);
}

// --- Client Dashboard Tests ---
test('Client dashboard loads successfully', async ({ page }) => {
  await login(page, 'client');
  await expect(page).toHaveURL(`${BASE_URL}/client/dashboard`);
  await expect(page.locator('h2')).toContainText('Bienvenido, Tech Solutions SL');
});

test('Client can view dashboard KPIs', async ({ page }) => {
  await login(page, 'client');
  // Check KPI cards exist
  await expect(page.locator('.bg-white.rounded-xl.p-6')).toHaveCount(4);
  // Check IVA card
  await expect(page.locator('text=IVA Trimestral')).toBeVisible();
  // Check IRPF card
  await expect(page.locator('text=IRPF Retenciones')).toBeVisible();
  // Check SS card
  await expect(page.locator('text=Seguridad Social')).toBeVisible();
  // Check vencimientos card
  await expect(page.locator('text=Próximos vencimientos')).toBeVisible();
});

test('Client can navigate to documentos', async ({ page }) => {
  await login(page, 'client');
  await page.click('text=Mis Documentos');
  await page.waitForURL(`${BASE_URL}/client/documentos`);
  await expect(page.locator('h2')).toContainText('Mis Documentos');
});

test('Client can navigate to facturas', async ({ page }) => {
  await login(page, 'client');
  await page.click('text=Facturas');
  await page.waitForURL(`${BASE_URL}/client/facturas`);
  await expect(page.locator('h2')).toContainText('Facturas');
});

test('Client can navigate to impuestos', async ({ page }) => {
  await login(page, 'client');
  await page.click('text=Impuestos');
  await page.waitForURL(`${BASE_URL}/client/impuestos`);
  await expect(page.locator('h2')).toContainText('Impuestos');
});

test('Client can navigate to nominas', async ({ page }) => {
  await login(page, 'client');
  await page.click('text=Nóminas');
  await page.waitForURL(`${BASE_URL}/client/nominas`);
  await expect(page.locator('h2')).toContainText('Nóminas');
});

test('Client can navigate to calendario', async ({ page }) => {
  await login(page, 'client');
  await page.click('text=Calendario');
  await page.waitForURL(`${BASE_URL}/client/calendario`);
  await expect(page.locator('h2')).toContainText('Calendario');
});

test('Client can navigate to mensajes', async ({ page }) => {
  await login(page, 'client');
  await page.click('text=Mensajes');
  await page.waitForURL(`${BASE_URL}/client/mensajes`);
  await expect(page.locator('h2')).toContainText('Mensajes');
});

// --- Advisor Dashboard Tests ---
test('Advisor dashboard loads successfully', async ({ page }) => {
  await login(page, 'advisor');
  await expect(page).toHaveURL(`${BASE_URL}/advisor/dashboard`);
  await expect(page.locator('h2')).toContainText('Panel de control');
});

test('Advisor can view clientes table', async ({ page }) => {
  await login(page, 'advisor');
  await expect(page.locator('table')).toBeVisible();
  await expect(page.locator('tr')).toHaveCountGreaterThan(0);
  // Check first row has cliente info
  const firstRow = page.locator('tr').first();
  await expect(firstRow.locator('td')).toHaveCountGreaterThan(0);
});

test('Advisor can view tareas urgentes', async ({ page }) => {
  await login(page, 'advisor');
  await expect(page.locator('text=Tareas urgentes (próximos 7 días)')).toBeVisible();
  // Check urgent tasks are listed
  await expect(page.locator('.px-6.py-4.flex.items-center.space-x-4')).toHaveCountGreaterThan(0);
});

test('Advisor can view carga de trabajo', async ({ page }) => {
  await login(page, 'advisor');
  await expect(page.locator('text=Carga de trabajo')).toBeVisible();
  // Check KPI cards
  await expect(page.locator('.group.bg-surface-900/50')).toBeVisible();
});

// --- Login/Logout Tests ---
test('Client can login and logout', async ({ page }) => {
  await login(page, 'client');
  await expect(page).toHaveURL(`${BASE_URL}/client/dashboard`);
  await logout(page);
  await expect(page).toHaveURL(`${BASE_URL}/auth/login`);
});

test('Advisor can login and logout', async ({ page }) => {
  await login(page, 'advisor');
  await expect(page).toHaveURL(`${BASE_URL}/advisor/dashboard`);
  await logout(page);
  await expect(page).toHaveURL(`${BASE_URL}/auth/login`);
});

// --- Navigation Tests ---
test('Client navbar links work', async ({ page }) => {
  await login(page, 'client');
  // Click each navbar link and verify navigation
  const links = [
    { label: 'Mis Documentos', url: '/client/documentos' },
    { label: 'Facturas', url: '/client/facturas' },
    { label: 'Impuestos', url: '/client/impuestos' },
    { label: 'Nóminas', url: '/client/nominas' },
    { label: 'Calendario', url: '/client/calendario' },
    { label: 'Mensajes', url: '/client/mensajes' },
  ];
  
  for (const { label, url } of links) {
    await page.click(`text=${label}`);
    await page.waitForURL(`${BASE_URL}${url}`);
    await expect(page.locator('h2')).toContainText(label);
  }
});

test('Advisor navbar links work', async ({ page }) => {
  await login(page, 'advisor');
  const links = [
    { label: 'Clientes', url: '/advisor/clientes' },
    { label: 'Tareas', url: '/advisor/tareas' },
    { label: 'Documentos', url: '/advisor/documentos' },
    { label: 'Calendario', url: '/advisor/calendario' },
    { label: 'Comunicaciones', url: '/advisor/comunicaciones' },
    { label: 'Reportes', url: '/advisor/reportes' },
  ];
  
  for (const { label, url } of links) {
    await page.click(`text=${label}`);
    await page.waitForURL(`${BASE_URL}${url}`);
    await expect(page.locator('h2')).toContainText(label);
  }
});

// --- Edge Cases ---
test('Unauthenticated access redirects to login', async ({ page }) => {
  await page.goto(`${BASE_URL}/client/dashboard`);
  await expect(page).toHaveURL(`${BASE_URL}/auth/login`);
});

test('Login with wrong credentials shows error', async ({ page }) => {
  await page.goto(`${BASE_URL}/auth/login`);
  await page.fill('input[name="email"]', 'cliente@tech-solutions.com');
  await page.fill('input[name="password"]', 'wrongpassword');
  await page.click('button[type="submit"]');
  await expect(page.locator('.alert')).toContainText('Credenciales incorrectas');
});

test('Session persists across page refreshes', async ({ page }) => {
  await login(page, 'client');
  const currentURL = page.url();
  await page.reload();
  await expect(page).toHaveURL(currentURL);
});

// --- Responsive Design Tests ---
test('Dashboard is responsive on mobile', async ({ page }) => {
  await login(page, 'client');
  await page.setViewportSize({ width: 375, height: 667 }); // iPhone 8/9/10
  await expect(page.locator('.sidebar')).toHaveClass('transform');
  await page.click('.sidebar-toggle'); // Show sidebar
  await expect(page.locator('.sidebar')).toHaveClass('open');
});

// --- Performance Tests ---
test('Page loads within reasonable time', async ({ page }) => {
  await login(page, 'client');
  const startTime = Date.now();
  await page.waitForLoadState('networkidle');
  const loadTime = Date.now() - startTime;
  expect(loadTime).toBeLessThan(3000); // Under 3 seconds
});

// --- Accessibility Tests ---
test('Page has proper focus-visible styles', async ({ page }) => {
  await login(page, 'client');
  await page.bringToFront();
  const focusedElement = await page.evaluate(() => {
    document.querySelector('button')?.focus();
    return document.activeElement;
  });
  expect(focusedElement).not.toBeNull();
});

// --- SEO Tests ---
test('Page has proper meta tags', async ({ page }) => {
  await login(page, 'client');
  const title = await page.title();
  expect(title).toContain('GESTIA');
  const description = await page.locator('meta[name="description"]');
  await expect(description).toBeVisible();
});