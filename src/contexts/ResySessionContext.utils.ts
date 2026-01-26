// Global reference for use in non-React code (like api.ts)
let globalShowSessionExpiredModal: (() => void) | null = null;

export function setGlobalSessionExpiredHandler(handler: () => void) {
    globalShowSessionExpiredModal = handler;
}

export function triggerSessionExpiredModal() {
    if (globalShowSessionExpiredModal) {
        globalShowSessionExpiredModal();
    }
}
