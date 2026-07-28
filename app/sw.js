// sw.js - O guardião que interceta os pedidos e serve do disco
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            // Se o vídeo estiver no disco (Cache API), entrega do disco. 
            // Se não estiver, baixa da rede.
            return response || fetch(event.request);
        })
    );
});
