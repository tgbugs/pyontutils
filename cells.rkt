;#lang racket  ; reminder that this breaks the repl :/
(require (for-syntax racket))
(require (for-syntax syntax/parse syntax/stx))
(require (for-syntax racket/match))
(require racket/trace)
;(require macro-debugger/stepper) ; such wow, very amaze!

;; define some functions to retrieve data for us...
(define-for-syntax NIFNEURON "NIFCELL:sao1417703748")
(define NIFNEURON "NIFCELL:sao1417703748") ; FIXME how to avoid this?
'(load-phenotypes)  ; load in all our phenotypes so they are known
'(load-neurons)  ; load existing neurons


; debug stuff
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
(begin-for-syntax
  (define-syntax-class pred
    #:attributes (p s)  ; for the future...
    (pattern (p s))))


(define-syntax (define-predicate stx) ; TODO need this to deal with conversion to intersections and restrictions...
  ;(displayln stx)
  (define (do-stx s)
    (displayln s)
    (syntax-parse s
      [(_ predicate:id) #'(define (predicate id label) (format "~a ~a ~a" id `predicate label))]))
  (let ([dp (car (syntax-e stx))]
        [stx-e (cdr (syntax-e stx))])
    (datum->syntax stx (cons 'begin (for/list ([s stx-e]) (do-stx (datum->syntax stx (list dp s))))))))

(define-predicate rdfs:label rdfs:subClassOf)

;; identifiers
(define-for-syntax (ilx-next-prod env)
  (define ilx-start 60000)
  (lambda () (begin0 (format "ilx:ilx_~a" ilx-start) (set! ilx-start (add1 ilx-start)))))
    
(define-for-syntax ilx-next (ilx-next-prod 'env))

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
     UBERON:1234
     hello
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

(define (phenotypes neuron-id . rest)
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
    (displayln (format "---------------- ~a" section)))
  stx-list)

(define test '(a (c 1) (b 2) (d 3)))

(define (redorder-by-pred lst [predicate-order '(b c d)])
  (#f))

(define (get-extras stx-list)
  (#f))

(define-syntax (neuron stx)
  "syntax to defer execution of parts of 'neuron until
  id has been filled in (and fill it in automatically)"

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
        (cond ((equal? dat 'neuron) (level (lambda (x) 'neuron-do) dat stx-list))
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
  '(neuron ; should be a macro i think... or just quoted... make code work later
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
  (neuron
    (extras #:label "wheeeeeee" #:id "ilx:ilx_999999" #:subClassOf NIFNEURON)
    (disjoint-union-of 'n10)
    (phenotypes 
      'p5
      '(edge2 . p2)
      '(edge1 . hello))))
