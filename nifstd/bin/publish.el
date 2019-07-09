;; [[nb:pyontutils::nifstd/resources/sawg.org::c746][publish]]
(require 'ox-publish)
(setq org-publish-project-alist
      `(("SPARC-anatomy"
         :components ("page"))
        ("page"
         :base-directory "../resources"
         :base-extension "org"
         :exclude ".*"
         :include ("sawg.org")
         :publishing-directory
         ,(let ((host (getenv "AUX_RESOLVER_HOST")))
           (format "/ssh:%s|sudo:nginx@%s:/var/www/ontology/trees/sparc/" (getenv "AUX_RESOLVER_HOST") (getenv "AUX_RESOLVER_HOST")))
         :publishing-function org-html-publish-to-html)
        ))
;; publish ends here
