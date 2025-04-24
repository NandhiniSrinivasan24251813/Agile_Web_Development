/**
 * Main JavaScript file for Epidemic Monitoring System
 */

$(document).ready(function () {
    // Initialize all Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize all Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-close alerts after 5 seconds
    $('.alert').each(function() {
        const $alert = $(this);
        if (!$alert.hasClass('alert-persistent')) {
            setTimeout(function() {
                $alert.alert('close');
            }, 5000);
        }
    });

    // Auto-focus first input in modal forms
    $('.modal').on('shown.bs.modal', function () {
        $(this).find('input:visible:first').focus();
    });

    // Confirm dangerous actions
    $('[data-confirm]').on('click', function(e) {
        const message = $(this).data('confirm') || 'Are you sure you want to proceed?';
        if (!confirm(message)) {
            e.preventDefault();
            return false;
        }
    });

    // Disable form submission on enter for certain forms
    $('.no-enter-submit').on('keypress', function(e) {
        return e.which !== 13;
    });

    // Custom file input label
    $('.custom-file-input').on('change', function() {
        let fileName = $(this).val().split('\\').pop();
        $(this).next('.custom-file-label').addClass("selected").html(fileName);
    });

    // Form validation styling
    (function() {
        'use strict';
        window.addEventListener('load', function() {
            // Fetch all forms we want to apply custom validation styles to
            const forms = document.getElementsByClassName('needs-validation');
            // Loop over them and prevent submission
            Array.prototype.filter.call(forms, function(form) {
                form.addEventListener('submit', function(event) {
                    if (form.checkValidity() === false) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                    form.classList.add('was-validated');
                }, false);
            });
        }, false);
    })();

    // Automatically update active state in navbar based on current URL
    const currentLocation = window.location.pathname;
    $('.navbar-nav .nav-link').each(function() {
        const navLink = $(this);
        const linkPath = navLink.attr('href');

        if (linkPath && currentLocation.startsWith(linkPath) && linkPath !== '/') {
            navLink.addClass('active fw-bold');
        } else if (linkPath === '/' && currentLocation === '/') {
            navLink.addClass('active fw-bold');
        }
    });

    // Tab functionality for custom tabs
    $('.tab-button').on('click', function() {
        const target = $(this).data('tab');

        // Update active tab button
        $('.tab-button').removeClass('active');
        $(this).addClass('active');

        // Show active tab content
        $('.tab-content').removeClass('active');
        $('#' + target).addClass('active');
    });

    // Add responsive table wrapper to all tables
    $('table:not(.table-fixed)').wrap('<div class="table-responsive"></div>');

    // Add lightbox effect to images
    $('.card img:not(.no-lightbox)').on('click', function() {
        const imgSrc = $(this).attr('src');
        if (imgSrc) {
            const modal = $('<div class="modal fade" tabindex="-1" role="dialog">');
            const content = $('<div class="modal-dialog modal-lg modal-dialog-centered" role="document">');
            const body = $('<div class="modal-content"><div class="modal-body p-0">');
            const img = $('<img class="img-fluid" src="' + imgSrc + '">');
            const close = $('<button type="button" class="btn-close position-absolute top-0 end-0 m-2" data-bs-dismiss="modal" aria-label="Close">');

            body.append(img).append(close);
            content.append(body);
            modal.append(content);

            $('body').append(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();

            modal.on('hidden.bs.modal', function() {
                modal.remove();
            });
        }
    });

    // Add copy button to code blocks
    $('pre code').each(function() {
        const $code = $(this);
        const $pre = $code.parent();

        const $copyBtn = $('<button class="btn btn-sm btn-outline-secondary copy-btn">Copy</button>');

        $pre.css('position', 'relative');
        $copyBtn.css({
            'position': 'absolute',
            'top': '5px',
            'right': '5px',
            'opacity': '0.7'
        });

        $copyBtn.on('click', function() {
            const text = $code.text();

            // Create temp element
            const $temp = $('<textarea>');
            $('body').append($temp);
            $temp.val(text).select();
            document.execCommand('copy');
            $temp.remove();

            // Change button text temporarily
            const $btn = $(this);
            const originalText = $btn.text();
            $btn.text('Copied!');
            setTimeout(function() {
                $btn.text(originalText);
            }, 2000);
        });

        $pre.append($copyBtn);
    });
});