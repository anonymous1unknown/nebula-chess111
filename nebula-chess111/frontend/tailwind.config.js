/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        nebula: {
          950: '#04020d',
          900: '#090618',
          800: '#120d2e',
          700: '#1c1545',
          600: '#271d5c',
          500: '#3d2d8a',
          400: '#5a44c0',
          300: '#7c63e8',
          200: '#a691f5',
          100: '#d1c6fb',
          50:  '#f0ecff',
        },
        cosmic: {
          gold:    '#f0b429',
          rose:    '#e84393',
          cyan:    '#22d3ee',
          green:   '#34d399',
          red:     '#f87171',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body:    ['"Inter"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'float':        'float 6s ease-in-out infinite',
        'pulse-slow':   'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer':      'shimmer 2s linear infinite',
        'glow':         'glow 2s ease-in-out infinite alternate',
        'piece-drop':   'pieceDrop 0.15s ease-out',
        'move-flash':   'moveFlash 0.4s ease-out',
        'check-pulse':  'checkPulse 0.6s ease-in-out',
      },
      keyframes: {
        float:      { '0%, 100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-10px)' } },
        shimmer:    { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        glow:       { from: { boxShadow: '0 0 10px #7c63e8' }, to: { boxShadow: '0 0 30px #7c63e8, 0 0 60px #3d2d8a' } },
        pieceDrop:  { '0%': { transform: 'scale(1.15)', opacity: '0.8' }, '100%': { transform: 'scale(1)', opacity: '1' } },
        moveFlash:  { '0%': { backgroundColor: 'rgba(240, 180, 41, 0.6)' }, '100%': { backgroundColor: 'transparent' } },
        checkPulse: { '0%, 100%': { boxShadow: '0 0 0 0 rgba(248, 113, 113, 0.7)' }, '50%': { boxShadow: '0 0 0 12px rgba(248, 113, 113, 0)' } },
      },
      backgroundImage: {
        'nebula-gradient': 'linear-gradient(135deg, #04020d 0%, #090618 40%, #120d2e 100%)',
        'card-gradient':   'linear-gradient(135deg, rgba(28,21,69,0.8) 0%, rgba(18,13,46,0.95) 100%)',
        'board-light':     'linear-gradient(135deg, #e8d5b7 0%, #d4b896 100%)',
        'board-dark':      'linear-gradient(135deg, #8b5e3c 0%, #6b4226 100%)',
      },
      backdropBlur: { xs: '2px' },
      boxShadow: {
        'nebula':   '0 0 0 1px rgba(124,99,232,0.3), 0 4px 24px rgba(61,45,138,0.4)',
        'piece':    '0 8px 24px rgba(0,0,0,0.6)',
        'board':    '0 20px 60px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.1)',
        'card':     '0 4px 24px rgba(0,0,0,0.4), 0 0 0 1px rgba(124,99,232,0.15)',
      },
    },
  },
  plugins: [],
}
