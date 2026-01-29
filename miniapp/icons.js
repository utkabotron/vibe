/**
 * VIBE Mini App - SVG Icon System
 * Apple 2025 Design System Icons
 */

const ICONS = {
    labour: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M17.5 8.33333L12.5 3.33333L11.25 4.58333L12.9167 6.25H7.08333L8.75 4.58333L7.5 3.33333L2.5 8.33333L7.5 13.3333L8.75 12.0833L7.08333 10.4167H12.9167L11.25 12.0833L12.5 13.3333L17.5 8.33333Z" fill="currentColor"/>
        <path d="M3.33333 15.8333V17.5H16.6667V15.8333H3.33333Z" fill="currentColor"/>
    </svg>`,

    paint: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M17.0833 6.66667L13.3333 2.91667L5 11.25V15H8.75L17.0833 6.66667ZM7.91667 13.3333H6.66667V12.0833L12.5 6.25L13.75 7.5L7.91667 13.3333Z" fill="currentColor"/>
        <path d="M2.5 17.5H17.5V15.8333H2.5V17.5Z" fill="currentColor"/>
    </svg>`,

    materials: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16.6667 4.16667V15.8333H3.33333V4.16667H16.6667ZM16.6667 2.5H3.33333C2.41667 2.5 1.66667 3.25 1.66667 4.16667V15.8333C1.66667 16.75 2.41667 17.5 3.33333 17.5H16.6667C17.5833 17.5 18.3333 16.75 18.3333 15.8333V4.16667C18.3333 3.25 17.5833 2.5 16.6667 2.5Z" fill="currentColor"/>
        <path d="M10 13.3333L6.66667 9.16667H8.33333V6.66667H11.6667V9.16667H13.3333L10 13.3333Z" fill="currentColor"/>
    </svg>`,

    defect: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M1.66667 17.5H18.3333L10 2.5L1.66667 17.5ZM10.8333 14.1667H9.16667V12.5H10.8333V14.1667ZM10.8333 10.8333H9.16667V7.5H10.8333V10.8333Z" fill="currentColor"/>
    </svg>`,

    plus: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M15.8333 10.8333H10.8333V15.8333H9.16667V10.8333H4.16667V9.16667H9.16667V4.16667H10.8333V9.16667H15.8333V10.8333Z" fill="currentColor"/>
    </svg>`,

    close: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M15.8333 5.34167L14.6583 4.16667L10 8.825L5.34167 4.16667L4.16667 5.34167L8.825 10L4.16667 14.6583L5.34167 15.8333L10 11.175L14.6583 15.8333L15.8333 14.6583L11.175 10L15.8333 5.34167Z" fill="currentColor"/>
    </svg>`,

    clock: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M9.99167 2.5C5.39167 2.5 1.66667 6.225 1.66667 10.8333C1.66667 15.4417 5.39167 19.1667 9.99167 19.1667C14.6 19.1667 18.3333 15.4417 18.3333 10.8333C18.3333 6.225 14.6 2.5 9.99167 2.5ZM10 17.5C6.325 17.5 3.33333 14.5083 3.33333 10.8333C3.33333 7.15833 6.325 4.16667 10 4.16667C13.675 4.16667 16.6667 7.15833 16.6667 10.8333C16.6667 14.5083 13.675 17.5 10 17.5Z" fill="currentColor"/>
        <path d="M10.4167 6.66667H9.16667V11.6667L13.5417 14.1917L14.1667 13.1583L10.4167 11.0417V6.66667Z" fill="currentColor"/>
    </svg>`,

    chevronDown: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5.58333 7.5L10 11.9083L14.4167 7.5L15.8333 8.91667L10 14.75L4.16667 8.91667L5.58333 7.5Z" fill="currentColor"/>
    </svg>`
};

/**
 * Get SVG icon by name
 * @param {string} name - Icon name
 * @returns {string} SVG markup
 */
function getIcon(name) {
    return ICONS[name] || '';
}
