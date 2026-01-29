/**
 * IndexedDB wrapper for VIBE Mini App
 * Handles offline storage for references and draft reports
 */

const DB_NAME = 'vibe_miniapp';
const DB_VERSION = 1;

const STORES = {
    REFERENCES: 'references',
    DRAFTS: 'drafts'
};

class VibeDB {
    constructor() {
        this.db = null;
    }

    /**
     * Initialize the database
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // References store (cached справочники)
                if (!db.objectStoreNames.contains(STORES.REFERENCES)) {
                    db.createObjectStore(STORES.REFERENCES, { keyPath: 'id' });
                }

                // Drafts store (черновики и pending отчёты)
                if (!db.objectStoreNames.contains(STORES.DRAFTS)) {
                    const draftsStore = db.createObjectStore(STORES.DRAFTS, { keyPath: 'id' });
                    draftsStore.createIndex('status', 'status', { unique: false });
                    draftsStore.createIndex('createdAt', 'createdAt', { unique: false });
                }
            };
        });
    }

    /**
     * Generic get operation
     */
    async get(storeName, key) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    /**
     * Generic put operation
     */
    async put(storeName, data) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put(data);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    /**
     * Generic delete operation
     */
    async delete(storeName, key) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.delete(key);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    /**
     * Get all records from a store
     */
    async getAll(storeName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    /**
     * Get records by index
     */
    async getByIndex(storeName, indexName, value) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(storeName, 'readonly');
            const store = transaction.objectStore(storeName);
            const index = store.index(indexName);
            const request = index.getAll(value);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    // === References Methods ===

    /**
     * Save references (справочники) to cache
     */
    async saveReferences(references) {
        const data = {
            id: 'main',
            ...references,
            updatedAt: Date.now()
        };
        return this.put(STORES.REFERENCES, data);
    }

    /**
     * Get cached references
     */
    async getReferences() {
        return this.get(STORES.REFERENCES, 'main');
    }

    /**
     * Check if references are fresh (less than 1 hour old)
     */
    async areReferencesFresh(maxAgeMs = 3600000) {
        const refs = await this.getReferences();
        if (!refs || !refs.updatedAt) return false;
        return (Date.now() - refs.updatedAt) < maxAgeMs;
    }

    // === Drafts Methods ===

    /**
     * Generate unique ID
     */
    generateId() {
        return 'draft_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Create a new draft
     */
    async createDraft(data) {
        const draft = {
            id: this.generateId(),
            status: 'draft',
            createdAt: Date.now(),
            syncedAt: null,
            retryCount: 0,
            projectId: null,
            projectName: null,
            productId: null,
            productName: null,
            actions: [],
            comment: '',
            ...data
        };
        await this.put(STORES.DRAFTS, draft);
        return draft;
    }

    /**
     * Update a draft
     */
    async updateDraft(id, updates) {
        const draft = await this.get(STORES.DRAFTS, id);
        if (!draft) throw new Error('Draft not found');

        const updated = { ...draft, ...updates };
        await this.put(STORES.DRAFTS, updated);
        return updated;
    }

    /**
     * Delete a draft
     */
    async deleteDraft(id) {
        return this.delete(STORES.DRAFTS, id);
    }

    /**
     * Get current draft (most recent with status 'draft')
     */
    async getCurrentDraft() {
        const drafts = await this.getByIndex(STORES.DRAFTS, 'status', 'draft');
        if (drafts.length === 0) return null;
        // Return most recent
        return drafts.sort((a, b) => b.createdAt - a.createdAt)[0];
    }

    /**
     * Get all pending reports (waiting to sync)
     */
    async getPendingReports() {
        return this.getByIndex(STORES.DRAFTS, 'status', 'pending');
    }

    /**
     * Mark draft as pending (ready to sync)
     */
    async markAsPending(id) {
        return this.updateDraft(id, { status: 'pending' });
    }

    /**
     * Mark report as synced
     */
    async markAsSynced(id) {
        return this.updateDraft(id, {
            status: 'synced',
            syncedAt: Date.now()
        });
    }

    /**
     * Increment retry count for failed sync
     */
    async incrementRetry(id) {
        const draft = await this.get(STORES.DRAFTS, id);
        if (!draft) return;

        return this.updateDraft(id, {
            retryCount: (draft.retryCount || 0) + 1
        });
    }

    /**
     * Get count of pending reports
     */
    async getPendingCount() {
        const pending = await this.getPendingReports();
        return pending.length;
    }

    /**
     * Clear all synced reports (cleanup)
     */
    async clearSyncedReports() {
        const synced = await this.getByIndex(STORES.DRAFTS, 'status', 'synced');
        for (const report of synced) {
            await this.delete(STORES.DRAFTS, report.id);
        }
    }
}

// Export singleton instance
const vibeDB = new VibeDB();
