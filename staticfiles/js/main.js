// static/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    // ── Inicializar tooltips de Bootstrap ─────────────────────
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(el => {
        if (typeof bootstrap !== 'undefined') {
            new bootstrap.Tooltip(el);
        }
    });

    // ── Auto-cerrar alertas flash despues de 5 segundos ───────
    // (complementa la animacion CSS del styles.css)
    setTimeout(function () {
        document.querySelectorAll('.alert').forEach(function (alert) {
            if (typeof bootstrap !== 'undefined') {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                if (bsAlert) {
                    bsAlert.close();
                }
            } else {
                alert.style.display = 'none';
            }
        });
    }, 5000);

    // ── Confirmacion antes de eliminar ────────────────────────
    // Uso en el template:
    // <button onclick="return confirmar('Eliminar este registro?')" form="formEliminar">Eliminar</button>
    window.confirmar = function (mensaje) {
        return confirm(mensaje || '¿Estás seguro?');
    };

    // ── Resaltar fila al hacer clic (navegacion intuitiva) ───────
    // Uso: <tr class="fila-link" data-href="{% url 'encomienda_detalle' enc.pk %}">
    document.querySelectorAll('.fila-link').forEach(function (fila) {
        fila.addEventListener('click', function () {
            if (this.dataset.href) {
                window.location = this.dataset.href;
            }
        });
    });
});
