;;; additional global settings for exporting docs -*- lexical-binding: t -*-

;; avoid orgstrap altogether when exporting docs, there should be no
;; cases where we need it, and in the rare case we do use a workaround
;; by e.g. adding an additional eval variable that is constant like
;; we do below because the exact text of the tutorial matters
(setq
 ignored-local-variables
 (cons 'orgstrap-block-checksum ignored-local-variables))

;; safe eval local variables
(setq
 safe-local-variable-values
 '((eval and noninteractive (defalias 'literal #'prin1-to-string))))

;; enable orgstrap-mode specifically to ignore orgstrap elvs which are hard to filter out otherwise
(orgstrap-mode)

;; settings needed to fix rendering issues
(defface cypher-pattern-face ; needs to run before ob-cypher is loaded
        '((t :foreground "DeepPink" :background unspecified :bold t))
        "Face for pattern struct." :group 'cypher-faces)

;; packages for babel languages
(use-packages
  cypher-mode
  dockerfile-mode
  json-mode
  jupyter
  ob-cypher
  ob-powershell
  racket-mode
  sparql-mode
  yaml-mode)

;; load babel languages
(org-babel-do-load-languages
 'org-babel-load-languages
 `((cypher . t)
   (sparql . t)
   (python . t)
   (shell . t)
   (jupyter . t)
   (powershell . t)))

;; set the default theme for rendering source blocks
(load-theme 'whiteboard t)  ; the t must be present

;; prevent rpm-spec-mode from inserting a blank template during export
(setq rpm-spec-initialize-sections nil)

;; org mode custom variables
(setq org-src-fontify-natively t)  ; this is t by default, so this is insurance
(setq org-export-with-broken-links t)  ; needed for hrefl among others

;; ignore headlines
(require 'ox-extra)
(ox-extras-activate '(ignore-headlines))

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
         (format "<a href=\"%s\">%s</a>" path (if desc desc path)))))
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

;; html export settings
(setq org-html-home/up-format
      ;; we have to do a little finagling to get this to work
      ;; but it should be sufficient to produce what we want
      (concat
       "<div style=\"position:float;top:0;\">
<span style=\"float:left;\"><a href=\"/docs\">Index</a> > %s</span>
<span style=\"float:right;\"><a href=\"%s\">"
       (and nil "\uf09b") ; emacs can render this, others cannot
       "Edit on GitHub</a></span><br><br></div>"))

(setq org-babel-exp-code-template
      (concat "#+html: <div id=\"%name\">\n"
              org-babel-exp-code-template
              "\n#+html: </div>"))

;; override `org-html-template' to get what we need
;; there doesn't seem to be any other way to do this
;; because the title h1 is always the first thing in the contents div
;; which is where the home and up links need to be for layout in readtheorg
(require 'ox-html)

(defun --org-html-link-helper (info)
  (let ((link-up (org-trim (plist-get info :html-link-up)))
        (link-home (org-trim (plist-get info :html-link-home))))
    (unless (and (string= link-up "") (string= link-home ""))
      (format (plist-get info :html-home/up-format)
              (or link-up link-home)
              (or link-home link-up)))))

(defun org-html-template (contents info)
  "Return complete document string after HTML conversion.
CONTENTS is the transcoded contents string.  INFO is a plist
holding export options."
  (concat
   (when (and (not (org-html-html5-p info)) (org-html-xhtml-p info))
     (let* ((xml-declaration (plist-get info :html-xml-declaration))
	    (decl (or (and (stringp xml-declaration) xml-declaration)
		      (cdr (assoc (plist-get info :html-extension)
				  xml-declaration))
		      (cdr (assoc "html" xml-declaration))
		      "")))
       (when (not (or (not decl) (string= "" decl)))
	 (format "%s\n"
		 (format decl
			 (or (and org-html-coding-system
                                  ;; FIXME: Use Emacs 22 style here, see `coding-system-get'.
				  (coding-system-get org-html-coding-system 'mime-charset))
			     "iso-8859-1"))))))
   (org-html-doctype info)
   "\n"
   (concat "<html"
	   (cond ((org-html-xhtml-p info)
		  (format
		   " xmlns=\"http://www.w3.org/1999/xhtml\" lang=\"%s\" xml:lang=\"%s\""
		   (plist-get info :language) (plist-get info :language)))
		 ((org-html-html5-p info)
		  (format " lang=\"%s\"" (plist-get info :language))))
	   ">\n")
   "<head>\n"
   (org-html--build-meta-info info)
   (org-html--build-head info)
   (org-html--build-mathjax-config info)
   "</head>\n"
   "<body>\n"
   ;;(--org-html-link-helper info) ; moved into content
   ;; Preamble.
   (org-html--build-pre/postamble 'preamble info)
   ;; Document contents.
   (let ((div (assq 'content (plist-get info :html-divs))))
     (format "<%s id=\"%s\" class=\"%s\">\n"
             (nth 1 div)
             (nth 2 div)
             (plist-get info :html-content-class)))
   ;; navigation links
   (--org-html-link-helper info)
   ;; Document title.
   (when (plist-get info :with-title)
     (let ((title (and (plist-get info :with-title)
		       (plist-get info :title)))
	   (subtitle (plist-get info :subtitle))
	   (html5-fancy (org-html--html5-fancy-p info)))
       (when title
	 (format
	  (if html5-fancy
	      "<header>\n<h1 class=\"title\">%s</h1>\n%s</header>"
	    "<h1 class=\"title\">%s%s</h1>\n")
	  (org-export-data title info)
	  (if subtitle
	      (format
	       (if html5-fancy
		   "<p class=\"subtitle\" role=\"doc-subtitle\">%s</p>\n"
		 (concat "\n" (org-html-close-tag "br" nil info) "\n"
			 "<span class=\"subtitle\">%s</span>\n"))
	       (org-export-data subtitle info))
	    "")))))
   contents
   (format "</%s>\n" (nth 1 (assq 'content (plist-get info :html-divs))))
   ;; Postamble.
   (org-html--build-pre/postamble 'postamble info)
   ;; Possibly use the Klipse library live code blocks.
   (when (plist-get info :html-klipsify-src)
     (concat "<script>" (plist-get info :html-klipse-selection-script)
	     "</script><script src=\""
	     org-html-klipse-js
	     "\"></script><link rel=\"stylesheet\" type=\"text/css\" href=\""
	     org-html-klipse-css "\"/>"))
   ;; Closing document.
   "</body>\n</html>"))
