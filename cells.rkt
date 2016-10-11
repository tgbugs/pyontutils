#lang racket  ; reminder that this breaks the repl :/
(require (for-syntax racket))
(require (for-syntax syntax/parse syntax/stx))
(require (for-syntax racket/match))
(require racket/trace)
(require macro-debugger/stepper) ; such wow, very amaze!

;; define some functions to retrieve data for us...
(define-for-syntax NIFNEURON "NIFCELL:sao1417703748")
(define NIFNEURON "NIFCELL:sao1417703748") ; FIXME how to avoid this?
'(load-phenotypes)  ; load in all our phenotypes so they are known
'(load-neurons)  ; load existing neurons

;; auto-quote macro
;(begin-for-syntax 
; (define-syntax (define-quote-args stx)  ; to high level just at the moment...
;   (syntax-parse stx
;     [(_ name:id args body) #'(define-syntax (name stx) body)]
;     [(_ name:id args doc:str body) #'(define-syntax name quote(args) doc body)])))

;; debug stuff
(begin-for-syntax
  (define-namespace-anchor a)                  ; <---
  (define ns (namespace-anchor->namespace a))  ; <---
  
  (define (pry ns) ; of course this fails to see local scope :/
    (let loop ()
      (display "PRY> ")
      (define x (read))
      (unless (or (eof-object? x) (equal? x '(unquote exit)))
        (pretty-print (eval x ns)) ; <---
        (loop)))))

;; neuron equivalent classes
(define (make-equivalent-neuron phenotype) ; TODO
  (write "should really do something about this\n"))

(define (equivalent-to . rest)
  (list rest))

;; predicates
(define edge-list '()) ; this is mutable so cannot pass it in as env...

(define (env-edge? env)
  (define (edge? expr)
    (member expr env)) ; syntax parse to make environment access to phenotypes nice?
  edge?)

(define (edge? expr) (member expr edge-list))

(begin-for-syntax
  (define-syntax-class pred
    #:attributes (p s)  ; for the future...
    (pattern (p s))))

(define-syntax (define-predicate stx) ; TODO need this to deal with conversion to intersections and restrictions...
  ;(displayln stx)
  (define (do-stx s)
    (displayln s)
    (syntax-parse s
      ;[(_ predicate:id) #'(begin (define (predicate id object) (format "~a ~a ~a" id `predicate object))
      [(_ predicate:id) #'(begin (define (predicate id object) (expand-predicate `predicate id object))
                                 (set! edge-list (cons `predicate edge-list)))]))
  (let ([dp (car (syntax-e stx))]
        [stx-e (cdr (syntax-e stx))])
    (datum->syntax stx (cons 'begin
                             (for/list ([s stx-e])
                               (do-stx (datum->syntax stx (list dp s))))))))

(define (expand-predicate predicate-name id object) ; TODO make this flexible?
  (define (expand-triple p s o)
    (list p s o))
  (cond ((and (list? object) (edge? (car object))) (map expand-triple object))
        (#t (expand-triple predicate-name id object)))) ; TODO check for real object?
  ;(format "~a ~a ~a" id predicate-name object))

(define-predicate
  rdf:type
  rdfs:label
  rdfs:subClassOf
  owl:disjointWith
  owl:onProperty
  owl:someValuesFrom
  ilx:hasExpressionPhenotype 
  ilx:hasMorphologicalPhenotype 
  )

(define-syntax (define-class stx) ; oh look how easy that copy paste was, thanks racket for being a pita
  ;(displayln stx)
  (define (do-stx s)
    (displayln s)
    (syntax-parse s
      ;[(_ predicate:id) #'(begin (define (predicate id object) (format "~a ~a ~a" id `predicate object))
      [(_ predicate:id) #'(begin (define predicate (symbol->string `predicate))
                                 (set! class-list (cons `predicate class-list)))]))
  (let ([dp (car (syntax-e stx))]
        [stx-e (cdr (syntax-e stx))])
    (datum->syntax stx (cons 'begin
                             (for/list ([s stx-e])
                               (do-stx (datum->syntax stx (list dp s))))))))

(define class-list '())
(define-class n1 n2 n3 n4 n5 n6)

(define-syntax (define-term stx)
  (define (define-and-set stx-list)
    (define syntax-obj #''predicate) ; default
    (define (do-stx s)
      (displayln (format "do-stx ~a" s))
      ;(displayln (syntax-original? syntax-obj))
      (cond ((equal? (syntax->datum syntax-obj) ''predicate)
             (syntax-parse s [thing:id #'(begin (define (thing id object) (expand-predicate `thing id object))
                                                (set! edge-list (cons `thing edge-list)))]))
            ((equal? (syntax->datum syntax-obj) ''class)  ; this is STUPID... there must be a better way to do this :/ urg continually fighting racket :/
             (syntax-parse s [thing:id (list #'(define thing (symbol->string 'thing))
                                                #'(set! class-list (cons `thing class-list)))]))
            (#t (error (format "~a ~a wtf" (syntax->datum syntax-obj) s)))))
        ;[thing:id syntax-obj]))
        ;[thing:id (datum->syntax stx syntax-obj)]))
    (define (check-for-type sl)
      (cond ((empty? sl) '())
            ((keyword? (syntax->datum (car sl))) (begin (displayln (format "SUCCESS ~a" (cadr sl)))
                                                        (set! syntax-obj (cadr sl)) ; FIXME kw name match?
                                                        (cddr sl))) ; drop the kw
            (#t (cons (car sl) (check-for-type (cdr sl))))))
    (define asdf (check-for-type stx-list))
    (displayln asdf)
    (map do-stx asdf))
    ;(map (lambda (s)
           ;(do-stx (datum->syntax stx (list (car (syntax-e stx))
                                            ;s))))
         ;asdf))

  (define asdf (define-and-set (cdr (syntax-e stx))))
  (displayln asdf)
  (datum->syntax stx (begin asdf)))

;(define-term #:syntax 'class rdf:type rdfs:label)  ; time to cut our losses :/

;; identifiers
(define-for-syntax (ilx-next-prod env)
  (define ilx-start 60000)
  (lambda () (begin0 (format "ilx:ilx_~a" ilx-start) (set! ilx-start (add1 ilx-start)))))
    
(define-for-syntax ilx-next (ilx-next-prod 'env))
(define ilx-next (ilx-next))

;; extras
(define-for-syntax (extras #:label label #:id (id ilx-next) #:subClassOf [subClassOf NIFNEURON] . rest)
  (if (procedure? id)
    (list 'extras (id) label subClassOf) ; TODO would be nice to use owl:subClassOf here...
    (list 'extras id label subClassOf)))

(define (extras id [label '()] [subClassOf '()])
  (list (list 'rdfs:label id label) (list 'rdfs:subClassOf id subClassOf)))

;; disjoint unions
(define (disjoint-union-of . rest)
  (cons 'disjoint-union-of rest)) ; TODO this doesn't quite work as we want it to...

;; phenotypes
(define pheno-list
  '( pyramidal
     basket
     large-basket
     parvalbumin
     somatostatin
     UBERON:1234
     hello
     fast-spiking
     p1
     p2
     p3
     p4
     ;p6 ; haha! error produced as expected :D
     p5))

(define (env-phenotype? env)
  (define (phenotype? expr)
    (member expr env)) ; syntax parse to make environment access to phenotypes nice?
  phenotype?)

(define phenotype? (env-phenotype? pheno-list))

(define (phenotypes- neuron-id . rest)
  "runtime function for phenotypes, neuron-id is filled in during phase1"
  (define (do-rest rest)
    (cond ((empty? rest) #t)
          ((cons? (car rest)) 'itsacons!)
          ((phenotype? (car rest)) 'itsapheno!)
          (#t (error (format "not pair or known phenotype ~a" rest))))
    (if (empty? rest)
      #t ; ok because empty triples are ok too
      (do-rest (cdr rest))))
  (if (do-rest rest)
    (map (lambda (r) (pheno-do neuron-id r)) rest)  ; FIXME neuron-id passing ;_;
    (error "phenotypes bad")))

(define (-and . rest)
  (cons 'and rest))

(define (pheno-get-edge pheno)
  'ilx:hasPhenotype) ; TODO using a define syntax on curie atoms might be fun... (c ilx:hasPhenotype)...

(define (pheno-pair-transform neuron-id pair)
  (list (car pair) neuron-id (cdr pair)))

(define (pheno-transform neuron-id pheno)
  (pheno-pair-transform neuron-id (cons (pheno-get-edge pheno) pheno)))

(define (pheno-do neuron-id pheno)
  (cond ((phenotype? pheno) (pheno-transform neuron-id pheno))
        ((equal? (car pheno) 'and) (map (lambda (r) (pheno-do neuron-id r)) (cdr pheno))) ; FIXME need to insert and ...
        ((and (cons? pheno) (member (cdr pheno) pheno-list))
         (pheno-pair-transform neuron-id pheno)) ; FIXME should probably check (phenotype? (cdr pheno))
        (#t (error (format "not a phenotype! ~a" pheno)))))

;; neuron
(define (neuron-do . rest) ; TODO use this to enforce evaluation order... may require a syntax object
  (append (car rest) (cdr rest)))

(define (neuron-do-wut . rest)
  (define id #f)
  (define (check-for-extras rest)
    (cond ((empty? rest) #f)
          ((equal? (caar rest) 'extras) (begin (set! id (cadr rest)) #t))
          (#t (check-for-extras (cdr rest)))))
  (if (check-for-extras rest)
    #t
    (set! rest (list id rest)))
  (define (check rest)
    ;(displayln rest)
    (cond ((empty? rest) #t)
          ;((equal? (caar rest) 'phenotypes) (set! phenotypes (cons id phenotypes))) ; TODO
          ((member (caar rest) '(extras phenotypes disjoint-union-of)) (check (cdr rest)))
          (#t #f)))
  (if (check rest)
    (list rest)
    (error (format "neuron is missing something! ~a" rest))))

;; neuron block manager
(define-for-syntax (reorder-sections stx-list)
  (define sections (map syntax->datum stx-list))
  (for ([prefix '(extras disjoint-union-of phenotypes)])
    (cond ((equal? #f #t) #f)
          (#t #f))
    (displayln (format "---------------- ~a" sections)))
  stx-list)

(define test '(a (c 1) (b 2) (d 3)))

(define (redorder-by-pred lst [predicate-order '(b c d)])
  (#f))

(define (get-extras stx-list)
  (#f))

(define-syntax (neuron-old stx) ; FIXME why do i need this?
  "syntax to defer execution of parts of 'neuron until
  id has been filled in (and fill it in automatically)"  ; we can do this more cleanly at run-time?

  (define id '())
  (define (set-id extras)
    (set! id (cadr extras))
    extras)

  (define (ins-id other)
    "insert missing args"
    (cons (car other) (cons id (cdr other))))

  (define (stx-do stx-list)
    (define (level func current next)
      (cons ((lambda (x) (datum->syntax (car next) (func x))) current) (stx-do (cdr next))))
    (if (empty? stx-list)
      '()
      (let* ([cars (car stx-list)]
             [dat (syntax->datum cars)]
             [d-func (lambda (x) (datum->syntax cars (ins-id x)))])
        (cond ((equal? dat 'neuron-old) (level (lambda (x) 'neuron-do) dat stx-list))
              ((equal? (car dat) 'extras) (level (lambda (x) (set-id (eval x))) dat stx-list))
              ((equal? (car dat) 'disjoint-union-of) (level d-func dat stx-list))
              ((equal? (car dat) 'phenotypes) (level d-func dat stx-list))
              (#t (displayln dat))))))
  (datum->syntax stx (stx-do (syntax-e stx))))

; steps should be
; 1) check for extras
; 2) if no extras add the id manually
; 3) inject the id into any other sections

; data (example)
(define syn (datum->syntax #f
  '(neuron-old ; should be a macro i think... or just quoted... make code work later
    (extras #:label "name") ; short label usually you don't want/need this
    (disjoint-union-of ''n1 ''n2 ''n3)
    (phenotypes ; FIXME
      '(edge1 . p1)
      '(edge2 . p2)
      'p3  ; bare phenotypes allowed... attempt inference?
      (-and 'p4 '(edge3 . p5))))))

(define inter (eval (syntax->datum syn)))

(define-predicate edge1 edge2 edge3)

(define bob
  (neuron-old
    (extras #:label "wheeeeeee" #:id "ilx:ilx_999999" #:subClassOf NIFNEURON)
    (disjoint-union-of 'n10)
    (phenotypes 
      'p5
      '(edge2 . p2)
      '(edge1 . hello))))

;; the pure function version makes a return!

(define (make-linker env)
  (define start 0)
  (lambda () (begin0 (format "linker_~a_~a" env start) (set! start (add1 start)))))
    
(define get-linker (make-linker 'env))

(define (restriction predicate object #:*ValuesFrom [*ValuesFrom owl:someValuesFrom])
  (define linker (get-linker))
  (list linker
        (rdf:type linker 'owl:Restriction) ; TODO a way to pass out the linker value...? also owl:Restriction type...
        (owl:onProperty linker predicate)
        (*ValuesFrom linker object)))

;(define (restriction a b)
 ;(list a b))

(define (lift-to-class triple)
  "utility method for lifting direct predicate usage
  to link classes, to the correct subClassOf Restriction
  version, make sure the triple is quoted..."
  (let ([res (restriction (car triple) (cddr triple))])
    (cons (rdfs:subClassOf (cadr triple) (car res))
            (cdr res))))

(lift-to-class '(edge1 "ilx:ilx_1234567" 'p2))

(define (phenotypes-get-missing-edges phenotype)
  (if (cons? phenotype)
    phenotype
    (cons 'ilx:hasPhenotype phenotype)))

(define (process-to-sub-or-dis . rest)
  (cons (cond ((empty? rest) '())
              ((cons? (car rest)) (rdfs:subClassOf (caar rest) (cdar rest)))
              (phenotype? (car rest) (rdfs:subClassOf 'ilx:hasPhenotype (car rest)))
              ((l-not? (caar rest)) (let ([pair (cdr (process-to-sub-or-dis (cdar rest)))])
                                      (owl:disjointWith (car pair) (cdr pair)))))
        (process-to-sub-or-dis (cdr rest))))

(define (phenotypes . rest)
  "phenotypes data, checks all the edges and phenos are known
  and then returns itself quoted"
  (define (check-rest rest)
    (cond ((empty? rest) '())
          ((l-not? (car rest)) (check-l-not-inner check-rest (cdr rest))) ; but then we need to missing...
          ((and (cons? (car rest))
                (not (cons? (caar rest))))
           (begin
             (displayln (caar rest))
             (check-rest (car rest))
             (check-rest (cdr rest))))
          ((and (edge? (car rest)) (phenotype? (cdr rest))) #t)
          ((phenotype? (car rest)) (begin (check-rest (cdr rest)) #t))  ; we do not expand missing edges here
          (#t (error (format "not pair or known phenotype ~a" rest)))))
  (if (check-rest rest)
    ;(cons 'phenotypes (map phenotypes-get-missing-edges rest))  ; FIXME neuron-id passing ;_;
    (cons 'phenotypes (map process-to-sub-or-dis rest))
    (error "phenotypes bad")))

; phenotypes expressions need to be more fully defined than just edge, target...
; then we can have expansion rules
'(phenotype edge target domain)
'(phenotype (l-not (edge . target))) ; negation, disjoint-with restriction on properpety edge, values from target
;'(phenotype (l-all (edge . target))) ; every, all, must, not actually possible to prove this... ever...
'(phenotype (l-some (edge . target))) ; present-in, found-in, (not (not))
;(phenotypes target) -> (list (phenotype target)) -> (list (l-some (restriction default-edge target))
;(define (phenotype-to-triples pheno)
  ;())

(define (sub-class-of . rest)
  ; context dependent predicate for making lists of subClassOf clauses
  (cons 'sub-class-of rest))

(define (disjoint-with . rest)
  ; context dependent predicate for making lists of disjoint-with clauses
  (cons 'disjoint-with rest))

(disjoint-with (restriction 'edge1 'p1))

(define (l-not . rest)  ; this needs to be implemented so that l-not gets passed the checking function of the enclosing form...
  "self evaluating: use is handled elsewhere (?seems like a bad idea...?)
  logical not which lifts to a disjointness
  statement for a phenotype expression"
  (cons 'l-not rest)) ; lol performance

(define (l-not? thing)
  (equal? 'l-not thing))

(define (check-l-not-inner check-function . inner)
  (check-function inner))

(define (expand-phenotypes phenotypes-data)
  ; to disjointWith or to subClassOf
  phenotypes-data)

(define (expand-disjoint-union-of disjoint-union-of-data)
  disjoint-union-of-data)

(define (neuron #:id [id ilx-next] #:label [label '()] #:subClassOf [subClassOf NIFNEURON] . rest)
  "this binds the defined phenotypes to an identifier
  much better process allows reuse of phenotypes sections"
  (when (procedure? id) (set! id (id)))
  (cons id
        (cons (rdfs:label id label)
              (cons (rdfs:subClassOf id subClassOf)
                    (map expand-sections rest)))))

(define (expand-sections section)
  (if (list? section)
    (cond ((equal? (car section) 'phenotypes) (expand-phenotypes section))
          ((equal? (car section) 'disjoint-union-of) (expand-disjoint-union-of section))
          (#t (error (format "ERROR unknown section heading: ~a" section))))
    (error (format "ERROR not a list: ~a" section))))

(define phil
  (neuron #:label "fast spiking interneuron" #:id "ilx:ilx_999999" #:subClassOf NIFNEURON
    (disjoint-union-of 'n10)
    (phenotypes 
      (l-not 'somatostatin) ; TODO -> put it in disjoint-with instead of sub-class-of
                            ; we also need to be able to do a namespace check...
      'fast-spiking ; these exist in the semi-namespace of phenotype classes
      '(ilx:hasExpressionPhenotype . parvalbumin)
      ;(cons 'ilx:hasExpressionPhenotype 'parvalbumin) ; ah the glories of a lisp-1
      '(ilx:hasMorphologicalPhenotype . large-basket))))

(define fully-expanded-neuron
  'triples-yo)

