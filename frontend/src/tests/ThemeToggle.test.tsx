import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeToggle } from '../components/ThemeToggle';

describe('ThemeToggle', () => {
  const localStorageMock = {
    getItem: vi.fn(),
    setItem: vi.fn(),
    clear: vi.fn(),
  };

  beforeEach(() => {
    Object.defineProperty(window, 'localStorage', {
      value: localStorageMock,
      writable: true,
    });
    document.documentElement.removeAttribute('data-theme');
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders theme toggle button', () => {
    localStorageMock.getItem.mockReturnValue(null);
    render(<ThemeToggle />);

    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('theme-toggle');
  });

  it('initializes with light theme when no saved preference', () => {
    localStorageMock.getItem.mockReturnValue(null);
    render(<ThemeToggle />);

    expect(screen.getByText('black')).toBeInTheDocument();
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('initializes with dark theme when saved preference is dark', () => {
    localStorageMock.getItem.mockReturnValue('dark');
    render(<ThemeToggle />);

    expect(screen.getByText('white')).toBeInTheDocument();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });

  it('toggles from light to dark on click', () => {
    localStorageMock.getItem.mockReturnValue(null);
    render(<ThemeToggle />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(screen.getByText('white')).toBeInTheDocument();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
  });

  it('toggles from dark to light on click', () => {
    localStorageMock.getItem.mockReturnValue('dark');
    render(<ThemeToggle />);

    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(screen.getByText('black')).toBeInTheDocument();
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
  });

  it('has correct aria-label for light theme', () => {
    localStorageMock.getItem.mockReturnValue(null);
    render(<ThemeToggle />);

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-label', 'Switch to black coffee');
  });

  it('has correct aria-label for dark theme', () => {
    localStorageMock.getItem.mockReturnValue('dark');
    render(<ThemeToggle />);

    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-label', 'Switch to white coffee');
  });

  it('saves theme to localStorage on initial render', () => {
    localStorageMock.getItem.mockReturnValue(null);
    render(<ThemeToggle />);

    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
  });
});
