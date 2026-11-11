function setTheme(themeName) {
    // Apply to the current page
    document.documentElement.setAttribute('data-theme', themeName);

    // Save to a cookie accessible by ALL *.achando.dev subdomains
    document.cookie = `theme=${themeName};domain=achando.dev;path=/;max-age=31536000;SameSite=Lax`;
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'catppuccin';
    setTheme(current === 'catppuccin' ? 'nord' : 'catppuccin');
}

// Run immediately on load to prevent flickering
const match = document.cookie.match(/(?:^|; )theme=([^;]*)/);
if (match) {
    setTheme(match[1]);
} else {
    setTheme('catppuccin'); // Fallback
}