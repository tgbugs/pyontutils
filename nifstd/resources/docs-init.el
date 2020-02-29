;;; additional global settings for exporting docs

;; set the default theme for rendering source blocks
(load-theme 'whiteboard t)  ; the t must be present

;; prevent rpm-spec-mode from inserting a blank template during export
(setq rpm-spec-initialize-sections nil)
