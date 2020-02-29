;;; additional global settings for exporting docs

;; set the default theme for rendering source blocks
(load-theme 'whiteboard t)  ; the t must be present

;; prevent rpm-spec-mode from inserting a blank template during export
(setq rpm-spec-initialize-sections nil)

;; org mode custom variables
(setq org-src-fontify-natively t)  ; this is t by default, so this is insurance
(setq org-export-with-broken-links t)  ; needed for hrefl among others

;; org link custom types
(require 'ol)  ; must require otherwise custom parameters wont stick

;; img tag links
;; NOTE these are for nested images inside other links NOT for images
(defun org-custom-link-img (path)
  (org-link-open-from-string path))
(defun org-custom-link-img-export (path desc format)
  (cond ((eq format 'html)
         (format "<a href=\"%s\"><img src=\"%s\"/></a>" desc path))))

;; TODO figure out how to suppress the message here
(org-link-set-parameters "img"
                         :follow #'org-custom-link-img
                         :export #'org-custom-link-img-export)

;; server local hrefs
(defun org-custom-hrefl (path)
  "do nothing because we don't know the context of the export")
(defun org-custom-hrefl-export (path desc format)
  "export a rooted path as an absolute href with no server"
  (cond ((eq format 'html)
         (format "<a href=\"%s\">%s</a>" path desc))))
(org-link-set-parameters "hrefl"
                         :follow #'org-custom-hrefl
                         :export #'org-custom-hrefl-export)

;; tramp links
(defun org-custom-tramp-export (path desc format)
  "Tramp links don't really "
  (cond ((eq format 'html)
         (format "<a href=\"tramp://%s\">%s</a>" path (or desc path)))))
(org-link-set-parameters "tramp"
                         :follow #'org-open-file
                         :export #'org-custom-tramp-export)
