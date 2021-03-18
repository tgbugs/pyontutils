#lang racket/base
(require plot
         racket/bool
         racket/contract
         racket/match
         racket/math
         racket/generic
         (only-in racket/list flatten)
         (only-in racket/hash hash-union)
         (for-syntax
          racket/base
          syntax/parse)
         )
(provide cospi
         sinpi
         make-periodic
         waveform-add
         waveform-concat
         )

(define (cospi x) (cos (* x (* 2 pi))))
(define (sinpi x) (sin (* x (* 2 pi))))

(define (cmb-constant level) (lambda (x) level))
; FIXME using combinators can lead to very difficult to debug errors
; e.g. if the inner function is used as the outer function you will
; get a cryptic error about application: not a procedure given: 0 etc.
; a runtime error with no backtrace (wat!?)
(define (constant x) 0) ; vs 1, constant means you can't scale it, you can only shift the reference level
(define (linear-transition-bad original terminal t-begin t-end)
  ; TODO contract on end > begin
  ; FIXME point slope scaling ... this is kind of beyond annoying
  ; need this to be composable for makepf
  (let* ([dx (- t-end t-begin)]
         [dy (- terminal original)]
         [slope (/ dy dx)])
    (if (= dx 0)
        (lambda (t)
          (if (< t t-begin)
              original
              ; FIXME for zero transitions check which where the quality goes
              terminal))
        (lambda (t)
          (cond ((< t-begin) original)
                ; FIXME pretty sure these should be 0 because we don't know what
                ; the state actually is, but if we due pure addition then original
                ; would be ok?
                ((> t-end) terminal)
                ; FIXME offset
                (else (* slope t)))))))

(define (linear-transition-hrm fun-state-begin fun-state-end)
  ; this is not right because fse will start at its zero
  ; not at t, which is ... bad
  (lambda (t-begin t-end)
    (let ([level-begin (fun-state-begin t-begin)]
          ; fun state end starts at zero not at time t?
          ; because we have to use the offset?
          [level-end (fun-state-end 0)])
      ; or do we force the average reference level in here
      ; no matter what?
      (lambda (t)
        (cond ((< t t-begin) level-begin)
              ((> t t-end) level-end)
              (else t))
        ))))

(define (linear-transition t)
  "A unitized linear transition."
  ; FIXME see how the interacts with scaling etc.
  (cond ((< t 0) 0)
        ((> t 1) 1)
        (else t)))

(define (positive-going-transition? original terminal) (< original terminal))
(define (negative-going-transition? original terminal) (> original terminal))

(module+ test-simple
  (plot (function cos 0 (* 2 pi)))
  (plot (function cospi 0 1))
  (plot (function sinpi 0 1))
  )
#;

(define (tf x) (+ offset (* amplitude (sin (+ (* f x)) ))))

(define-generics has-level
  (apply-level has-level))
; takes a level and a level combinator probably more complex than it
; needs to be but this way we can delegate how level is set to the
; combinator
(struct waveform-state (level combinator)
  #:methods gen:has-level
  [(define (apply-level ws)
     ((waveform-state-combinator ws) (waveform-state-level ws)))])

(define (dy state-begin state-end)
  (apply - (map waveform-state-level (list state-end state-begin))))

(define (dl state-begin state-end t-transition-begin)
  (apply - (map (lambda (st)
                  (let-values ([(s t) (apply values st)])
                    (let ([f ((waveform-state-combinator s) (waveform-state-level s))])
                      (f t))))
                (list (list state-end 0) (list state-begin t-transition-begin)))))

(define (dl-new f-state-beg-t->l f-state-end-t->l t-transition-begin)
  (- (f-state-end-t->l 0) (f-state-beg-t->l t-transition-begin)))

(define (dln fun-s-b
             fun-s-e
             beg-t)
  (- (fun-s-e 0) (fun-s-b beg-t)))

(module+ test-dl
  (dl (waveform-state 0 cmb-constant) (waveform-state 1 cmb-constant) 1)
  (dln (cmb-constant 0) (cmb-constant 1) 1)

  )

(define (dlno cmb-s-b
             cmb-s-e
             lvl-s-b
             lvl-s-e
             beg-t)
  (- ((cmb-s-b lvl-s-b) 0) ((cmb-s-e lvl-s-e) beg-t)))

(define (make-ft dl dt ln tn)
  (if (= 0 dt)
      (lambda (t) (error "This should never be called, dt has zero width."))
      (let ([slope (/ dl dt)])
        (let ([intercept (- ln (* slope tn))])
          (lambda (t) (+ (* slope t) intercept))))))

(define (transition-linear dl dt lvl timepoint)
  ;(println (format "derp: ~a ~a ~a ~a" dl dt lvl timepoint))
  (if (= 0 dt)
      (lambda (t) (error "This should never be called, dt has zero width."))
      (let ([slope (/ dl dt)])
        (let ([intercept (- lvl (* slope timepoint))])
          (lambda (t) (+ (* slope t) intercept))))))

(define euler (exp 1))

;;; transitions
;; there are two major families of transitions those that have
;; definite start and end times and those that only have start times
;; and where the second state is not constant but is in fact only
;; asymtotic and never technically achieved this means that there are
;; also two families of pulses as a result

;; one way out of this would be to always use piece-wise functions
;; so that they are at least continuous where possible this means
;; the filling in rule is a bit trickier?

(define (cmb-trans-exponential tau)
  "Tau is the exponential time constant."
  ; FIXME this is demonstrably wrong
  ; there is no such thing as an exponential transition

  ; FIXME this is a bit tricky because the exponential
  ; should skip to the next state, but it may not
  #; ; this is the old version which assumes that there is a time off
  (define (transition-exponential dl dt lvl timepoint)
    #;(transition-exponental lvl-beg lvl-end beg-t-n end-t-n)
    ; FIXME lvl and timepoint probably have to be the start timepoint
    ; for sanity and consistency, only the linear transitions don't care
    (let ([tau (/ dt euler)]) ; FIXME exponential pulse
      (lambda (t) (+ lvl (* dl (- 1 (expt euler (- (/ (- t timepoint) tau)))))))))
  (define (transition-exponential dl offset timepoint)
    ; do we really need the transition here or should we force the correction?
    ; by the upstream user? Probably not. We should do it here.
    (lambda (t) (+ offset (* dl (- 1 (expt euler (- (/ (- t timepoint) tau))))))))
  transition-exponential)

(define transition-exponential (cmb-trans-exponential 1)) ; XXX does not exist


(define (transition-unspecified dl dt offset-at-begin time-begin)
  (lambda (t) +nan.0))

(define desc-pulse
  '(
    ; describing pulses
    ;       _|_
    ; _/\_  _||_
    ; _/'\_ _|'|_ _.-._
    ; _/-._ _|'\_ _.-|_
    ; _.-\_ _/'|_ _|-._
    ;
    ;       imp
    ; tri   imp
    ; trap  sqr   xpxp
    ; lnxp  sqln  xpsq
    ; xpln  lnsq  sqxp
    ;
    ; _  base state
    ; /  transition with end time
    ; .- transition with only begin time and without end time
    ; '  a reachable end state
    ; |  a transition with a begin and end time that are the same
    ;
    ; piece wise functions with varying numbers of parameters
    ; I think it is better to deal with exponential as if it were triangular
    ; and push the complexity of dealing with pulse shape into the calculation of tau
   ))

(define (cmb-transition-expt tau)
  ; the primary reason why it is hard to use this righ now is because we assume 4 timepoints
  ; and the 3 timepoint case is ambiguous _/-\_ vs _.-\_ vs _/-._
  (define (transition-expt dl _ offset-at-begin time-begin)
    (λ (t) (+ offset-at-begin (* dl (- 1 (expt euler (- (/ (- t time-begin) tau))))))))
  transition-expt)

(define (pulse-interface-0
         time-begin-transition-1
         duration-transition-1
         duration-state-2
         duration-transition-2)
  #f)

; IEEE 181 figures 2-6 are the most useful here though not at all useful for consistent
; naming of repeated state occurnaces, fortunately we can just use occurrence-n which matches
; the ordered pair (s n) in the specification
; figure 8 is critical of understanding why duration-state-occurrence is NOT the same
; as pulse duration
(define (pulse-interface-1
         pulse-duration
         pulse-separation
         pulse-period
         ; BIG NOTE do not confuse use pulse-duration with
         ; duration-state-2-ococurance-1 because it is from transition
         ; occurrence instant to transition occurrence instant, NOT
         ; from the end of the transition, defined at 10, 50 and 90%
         ; reference levels

         time-begin-state-1-occurrence-1 ; expt
           duration-state-1-occurrence-1 ; expt
           time-end-state-1-occurrence-1 ; expt

         time-begin-transition-1 ; expt
           duration-transition-1
           time-end-transition-1

         time-begin-state-2-occurrence-1
           duration-state-2-occurrence-1
           time-end-state-2-occurrence-1

         time-begin-transition-2 ; expt
           duration-transition-2
           time-end-transition-2

         time-begin-state-1-occurrence-2
           duration-state-1-occurrence-2
           time-end-state-1-occurrence-2

         )
  ; valid combinations
  #f)

(define (pulse-interface-w/-expt
         time-begin-state-1-occurrence-1
           duration-state-1-occurrence-1
           time-end-state-1-occurrence-1

         time-begin-transition-1

         time-begin-transition-2

         )
  #f)

(define (terse
         #:beg-s-1-1  [beg-s-1-1 0] ; this is pretty much always zero
         #:dur-s-1-1  dur-s-1-1
         #:end-s-1-1  end-s-1-1

         #:beg-t-1    beg-t-1
         #:dur-t-1    dur-t-1
         #:end-t-1    end-t-1

         #:beg-s-2-1  beg-s-2-1
         #:dur-s-2-1  dur-s-2-1
         #:end-s-2-1  end-s-2-1

         #:beg-t-2    beg-t-2
         #:dur-t-2    dur-t-2
         #:end-t-2    end-t-2

         #:beg-s-1-2  beg-s-1-2
         #:dur-s-1-2  dur-s-1-2
         #:end-s-1-2  end-s-1-2
         )
  ; things that must be equal if both are present
  (= end-s-1-1 beg-t-1)
  (= end-t-1 beg-s-2-1)
  (= end-s-2-1 beg-t-2)
  (= end-t-2 beg-s-1-2)
 )

(module+ test-pir

  (plot (function (family-pulse-new 1 2 3 4
                                    0 1
                                    cmb-constant
                                    transition-linear
                                    cmb-constant
                                    transition-linear)
                  0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))

  ; super happy with this right now
  (plot (function (pulse-invariant-repr #:beg-t-1   1
                                        #:dur-t-1   1
                                        #:dur-s-2-1 1
                                        #:dur-t-2   1
                                        #:end-s-1-2 4)
                  0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))

  (plot (function (pulse-invariant-repr #:beg-t-1   1
                                        #:dur-t-1   1
                                        #:dur-s-2-1 1
                                        #:dur-t-2   1
                                        #:end-s-1-2 4
                                        #:cmb-t-1 transition-linear
                                        #:cmb-t-2 transition-linear
                                        )
                  0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))

  #; ; exponential transitions do no exist and +cannot+ thus
  ; absolutely can hurt you /me dies laughing, yeah, they exist, they
  ; just don't have an end time, so you can't use the same underlying
  ; abstraction for this, or maybe we can? the outsiders await to
  ; devour the foolish
  (plot (function (pulse-invariant-repr #:beg-t-1   1
                                        #:dur-t-1   1
                                        #:dur-s-2-1 1
                                        #:dur-t-2   1
                                        #:end-s-1-2 4
                                        #:cmb-t-1 transition-exponential
                                        #:cmb-t-2 transition-exponential
                                        )
                  0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))
  )

(define (cmb-pulse-transitions
         #:beg-t-1   beg-t-1
         #:dur-t-1   dur-t-1
         #:dur-s-2-1 [dur-s-2-1 #f]
         #:end-s-2-1 [end-s-2-1 #f]
         #:dur-t-2   dur-t-2
         #:end-s-1-2 end-s-1-2
         #:lvl-s-1 [lvl-s-1 0]
         #:lvl-s-2 [lvl-s-2 1]
         #:amp [amp 1]
         #:off [off 0]

         #:cmb-s-1-1 [cmb-s-1-1 cmb-constant]
         #:cmb-t-1   [cmb-t-1   transition-unspecified]
         #:cmb-s-2-1 [cmb-s-2-1 cmb-constant]
         #:cmb-t-2   [cmb-t-2   transition-unspecified]
         )
  ; FIXME ideally though perhaps in what would be considered a bad
  ; design it should be possible to reparameterize different things at
  ; different times by being able to pass values at a later stage?
  (define (cmb-pulse-cmb
           #:lvl-s-1 [lvl-s-1 0]
           #:lvl-s-2 [lvl-s-2 1]

           #:cmb-s-1-1 [cmb-s-1-1 cmb-s-1-1]
           #:cmb-t-1   [cmb-t-1   cmb-t-1]
           #:cmb-s-2-1 [cmb-s-2-1 cmb-s-2-1]
           #:cmb-t-2   [cmb-t-2   cmb-t-2]
           )
    (pulse-invariant-repr)
    )
  cmb-pulse-cmb)

#;
; ARGH WTF or/c is NOT actually or !
; it can't match more than one ! GRRRRR
; SIGH this is actually a one-of/c like
; json SIGH SIGH SIGH
; and LOL also first-or/c doesn't work
; because somehow it doesn't keep going
; to try to find one that works

(provide (contract-out [transition (first-or/c
                                    (->i (#:end [end number?]
                                          #:beg [beg number?]
                                          #:dur [dur number?])
                                         #:pre (beg dur end) (= (+ beg dur) end)
                                         any)
                                    (->i (#:beg [beg number?]
                                          #:dur [dur number?])
                                         any)

                                    (->i (#:beg [beg number?]
                                          #:end [end number?])
                                         any))]))
#; ; sigh
(provide (contract-out [transition (or/c (->* (#:beg number?
                                               #:dur number?) any)
                                         ; sigh surely there is a way to
                                         ; do this without having to duplicate
                                         ; the #:beg, but ->i doesn't seem to work
                                         ; for optional arguments
                                         (->* (#:beg number?
                                               #:end number?) any)
                                         )]))
; ->i is the combinator we want to express invariants over inputs or outputs?
; don't use ->d it is deprecated, can't use ->* because we have to be able
; to refer to both dur and end to compare them

#;
(provide (contract-out [transition (->i (#:beg [beg number?])
                                        (#:dur [dur number?]
                                         #:end [end number?])
                                        #:pre (beg dur end) (or dur end)
                                        #:pre (beg dur) #t
                                        #:pre (beg end) #t
                                        ;#:pre (dur) dur
                                        ;#:pre (end) end
                                        ;#:pre () #f
                                        any)]))
#;
(provide (contract-out [transition (->i (#:beg [beg number?])
                                        (#:dur [dur number?]
                                         #:end [end number?])
                                        ; LOL NOW it doesn't work !??!?!?!
                                        #:pre (beg dur end) (= (+ beg dur) end)
                                        any)]))

(provide
 (contract-out [transition (->i (#:beg [beg number?])
                                (#:dur [dur number?]
                                 #:end [end number?])
                                #:pre (beg dur end) ; XXX this isn't actually correct
                                ; One of #:dur or #:end must be supplied, for both ensure same point.
                                (let ([ud (unsupplied-arg? dur)]
                                      [ue (unsupplied-arg? end)])
                                  (and (nand ud ue)
                                       (or ud ue (and (= end (+ beg dur))))))
                                any)]))

(define (transition #:beg beg #:dur [dur #f] #:end [end #f])
  ; lol actually neither dur nor end are required because
  ; that was the whole point hahahahaha I don't neve need this
  ; hoever for certain families of transition you do want this
  #;
  (unless (or dur end)
    (error "need one of #:dur or #:end"))
  #;
  (when (and dur end (not (= end (+ beg dur))))
    (error "begin + duration != endpoint"))
  (values beg (or end (+ beg dur))))

(module* hrm-1 racket/base
  (require (submod ".."))
  (transition #:beg 0 #:dur 1)
  #;
  (transition #:beg 0 #:dur 1 #:end 1)
  )
(module* hrm-2 racket/base
  (require (submod ".."))
  (transition #:beg 0)
  )
(module* hrm-3 racket/base
  (require (submod ".."))
  (transition #:beg 0 #:dur "")
  (transition #:beg 0 #:dur #f)
  )

(define (pulse-invar-2
         t-1
         t-2
         )
  ; in their most reduced form pulses are described by two transition
  ; functions there aren't actually state functions independent of
  ; those, the only timepoint that matters externally is when the
  ; next transition occurs, unfortunately this means that we have
  ; to know the internal temporal structure of the pulse function
  ; if it depends on some other duration, so we would still want
  ; a separate interface, this means that _this_ interface has to
  ; work with the functions and not the combinators, which sort of
  ; defeats the point, thus I think the best approach is to keep
  ; the families separate or somehow provide a way to generate something
  ; that looks like the exponential version from the trap version
  ; OR maybe we just leave it to the users to realize that you
  ; can't use a transition only function with a transition + state?

  ; how do you deal with transitions at the boundaries of exponential epochs?
  #f
  )

(module+ test-new
  (let* ([f-prep (cmb-transition-expt 0.5)]
         [f-t (f-prep -1 #f 1 3)])
    (map f-t '(3 4 5)))
  (define ftri (pulse-invariant-repr
                ; triangular
                #:beg-t-1  1
                #:beg-t-2  2
                #:dur-t-2  1
                #:cmb-t-1  transition-linear
                #:cmb-t-2  transition-linear))
  (plot (function ftri 0 5 #:width 3 #:y-max 1.5 #:color 8 #:style 0))
  (define fexp #f)
  (set! fexp (pulse-invariant-repr
              #:beg-t-1 1
              #:beg-t-2 2
              #:cmb-t-1 (cmb-transition-expt 0.5)
              #:cmb-t-2 (cmb-transition-expt 0.5)))
  (define (dtau tau beg-t-2)
    (let ([texp (cmb-transition-expt tau)])
      (pulse-invariant-repr
       #:beg-t-1 1
       #:beg-t-2 beg-t-2
       #:cmb-t-1 texp
       #:cmb-t-2 texp)))
  (plot (function fexp 0 5 #:width 3 #:y-max 1.5 #:color 8 #:style 0))
  (plot `(,(axes)
          ,@(map (λ (tau beg-t-2 color)
                   (function (dtau tau beg-t-2) 0 7
                             #:width 3
                             #:y-max 1.5
                             #:color color
                             #:style 0))
                 '(0.1 0.2 0.5  1)
                 '(  2   2   3  4)
                 '(  1   2   3  4))))
  ; FIXME so here is the problem, at the end of the day
  ; you are going to want to be able to parameterize
  ; and iterate over literally any and all of the possible
  ; parameters and variables, and you don't want to have to
  ; rewrite the function signature every time you want to
  ; add a new feature
  ; so yes, I have now sparsified the pulse representation sufficiently
  ; and we can deal with triangular, rectangular, and trapezoidal transitions
  ; for all cases BUT now we need to come back and deal with the constant and variable
  ; problem and how to make it extensible, I'm guessing lots of keywords since I'm not
  ; wanting to venture too far into racket language features
  )

(define (pulse-invariant-repr
         ; transition times and durations
         #:beg-t-1    beg-t-1

         #:dur-t-1   [dur-t-1 #f] ; FIXME this is not required for transitions that only have an onset time

         #:dur-s-2-1 [dur-s-2-1 #f] ; +one of these two is required+
         ;#:end-s-2-1 [end-s-2-1 #f] ; if end-s-2-1 is provided it must be greater than beg+dur-t-1

         #:beg-t-2   [beg-t-2 #f] ; use this because sometimes there isn't really a state 2
         ; only one of dur-t-1 dur-s-2-1 or beg-t-2 is required

         #:dur-t-2   [dur-t-2 #f]

         ; FIXME we don't actually do anything with this right now because
         ; pulses aren't epochs
         ;#:dur-s-2-1 dur-s-1-2 ; FIXME do we allow this? it breaks the modular epoch assumption
         ; we don't need this, it is a proxy for epoch
         ; FIXME the only issue here is that we will need/want a way to introspect
         ; when epochs are created so that we can tell that maybe we cut a transition short
         ; without having to inspect it
         ;#:end-s-1-2 end-s-1-2 ; one of these two is required

         ; state levels ; present in all cases
         #:lvl-s-1 [lvl-s-1 0]
         #:lvl-s-2 [lvl-s-2 1]
         ; an alternate and possibly more useful set of invariants
         #:amp [amp 1]
         #:off [off 0]
         ;#:waveform-amplitude waveform-amplitude
         ;#:offset offset

         ;#:defer-cmb #f ; don't do it this way ?

         ; state and transition functions
         ;#:cmp-pulse-in  [cmb-pulse-in]
         ;#:cmp-pulse-out [cmb-pulse-out]

         #:cmb-s-1-1 [cmb-s-1-1 cmb-constant]
         #:cmb-t-1   [cmb-t-1   transition-unspecified]
         #:cmb-s-2-1 [cmb-s-2-1 cmb-constant]
         #:cmb-t-2   [cmb-t-2   transition-unspecified]
         #;
         #:cmb-s-1-2
         #;
         [cmb-s-1-2 constant])
  "This is by far the most useful set of input arguments because it
minimizes the number of values that have to change over all possible
cases.

States numbers are assigned by the ordering of their first occurance in time.

The divergence from the 181 standard here due to the fact that we need
the numbering of states to be invariant to their levels so that the
function can work for positive and negative state transitions.

This is the otherwise specified notice that is required by note 1
under the definition of state for 181 2011 on page 8 (p20 in the pdf)."
  ; The cases Where it is not as efficient would be where the params
  ; of only a single transition change but the other transition needs
  ; to remain locked in time.  In those cases an additinal invariant
  ; must be specified which either that the sum of t-" the best
  ; internal invariant representation that we have choosen
  ; there are a number of possible combinations, the simplest being
  ; to use end-s-2-1 or beg-t-2, these are equivalent to a number
  ; of other invariants expressed as sums of previous durations

  ; given the general desire to be able to support both use cases
  ; either dur-s-2-1 OR end-s-2-1 may be provided

  #; ; this logic doesn't make sense anymore
  (when (and beg-t-2 dur-t-1)
    ; FIXME make this a contract
    (unless (<= (+ beg-t-1 dur-t-1) beg-t-2)
      (error "Invariant violated.")))
  ; aside: this is a perfect example of when you want to use let*
  (unless (or dur-t-1 beg-t-2)
    (error "either need a duration for t-1 or a begin time for t-2"))
  (let* ([end-t-1 (if dur-t-1 (+ beg-t-1 dur-t-1) beg-t-2)]
         [dur-s-2-1 (if dur-s-2-1 dur-s-2-1 0)] ; my elisp is leaking
         [beg-t-2 (or beg-t-2 (+ end-t-1 dur-s-2-1))]
         [end-t-2 (if dur-t-2 (+ beg-t-2 dur-t-2) #f)])

    #; ; FIXME need a way to introspect this after the closure
    (when end-s-1-2
      ; FIXME make this a contract
      (unless (<= end-t-2 end-s-1-2)
        (error "Invariant violated.")))

    (family-pulse-new beg-t-1 end-t-1 beg-t-2 end-t-2
                      lvl-s-1
                      lvl-s-2
                      cmb-s-1-1
                      cmb-t-1
                      cmb-s-2-1
                      cmb-t-2)))

(λ (cmb-f cmb-g)
  (λ (tn ln)
    (λ (t) (cmb-f )))
  )

(define (family-pulse-new
         ; transition times
         t1 t2 t3 t4
         ; state levels
         lvl-s-1
         lvl-s-2
         #; s-1-2 ; TODO do we have a use case for this having a
         ; different generating function or do we follow the standard
         ; and say that any change in the underlying state, including
         ; ones not discussed in the standard, needs to have a
         ; separate number, or do we follow the standard strictly and
         ; only care about the specified reference level?

         ; state and transition functions
         cmb-s-1-1
         cmb-t-1
         cmb-s-2-1
         cmb-t-2
         #;
         fun-s-1-2)
  "This is the full internal representation layer."
  #f
  ; FIXME remote state struct ... ?
  ; HAH amusingly the dl and dt values are nearly the invariant
  ; values we had before/above, in point of fact, we could drop
  ; even needing to list the state-1 level ... and only list the
  ; change in level, but that seems ... HRM
  (let ([dt-1 (if t2 (- t2 t1) (- t1 t3))]
        [dt-2 (if t4 (- t4 t3) #f)]
        [fun-s-1-1 (cmb-s-1-1 lvl-s-1)]
        [fun-s-2-1 (cmb-s-2-1 lvl-s-2)])
    ;[dl-1 (dy s1 s2)]
    ;[dl-2 (dy s2 s1)]
    ; XXX need feedback
    (let ([dl-1 (dln fun-s-1-1 fun-s-2-1 t1)]
          ; FIXME yep, these are all coming back as zero
          [dl-2 (dln fun-s-2-1 fun-s-1-1 #; fun-s-1-2 t3)])
      ;[l-1 (waveform-state-level s1)]
      ;[l-2 (waveform-state-level s2)]
      (let* ([fun-t-1 (cmb-t-1 dl-1 dt-1 lvl-s-1 t1)]
             [real-dl-2 (if (and t2 (not (= t2 t3)))
                            (fun-s-2-1 t3)
                            (fun-t-1 t3))]
             [fun-t-2 (cmb-t-2 (- real-dl-2) dt-2 (+ lvl-s-1 real-dl-2) t3)])
        (println (format "FIXME line: ~a ~a ~a ~a" dl-2 dt-2 lvl-s-2 t3))
        (lambda (t)
          (cond [(< t t1) (fun-s-1-1 t)]
                [(and t2 (< t t2)) (fun-t-1 t)]
                [(< t t3) (fun-s-2-1 (- t t2))]
                ; FIXME we could normalize the transitions so that
                ; they were always normalized to start at t=0, but
                ; it seems more efficient to encode the values in
                ; the constants rather than subtract the time offset
                ; like we have to do for the non-transition periods
                [(and t4 (< t t4)) (fun-t-2 t)]
                ; FIXME don't do this branch in here we can detect it before we return the lambda
                [t4 (fun-s-1-1 (- t t4))]
                [else (fun-t-2 t)]
                ))))))

(define (family-pulse s1 s2 t1 t2 t3 t4 [comb-trans transition-unspecified])
  "the ur family"
  ; TODO interface for alternate ways of specifying pulse parts that are more invariant
  ; transition-1-onset
  ; transition-1-duration
  ; state-2-duration
  ; transition-2-duration
  ;
  ; FIXME ordering restrictions on times
  (let ([f-1 (apply-level s1)]
        [f-2 (apply-level s2)]
        ; FIXME dl almost certainly should be calculated to for continuous transitions
        ; with the state function not with the reference level for that function ?
        ; this is something that needs to be clarified, that or all periodic state
        ; functions cannot be arbitrary but must start at zero? seems bad
        ;[dl-1 (dy s1 s2)]
        ;[dl-2 (dy s2 s1)]
        ; XXX need feedback
        [dl-1 (dl s1 s2 t1)]
        [dl-2 (dl s2 s1 t3)]
        [l-1 (waveform-state-level s1)]
        ;[l-2 (waveform-state-level s2)]
        [dt-1 (- t2 t1)]
        [dt-2 (- t4 t3)])
    (let ([ft-1->2 (comb-trans dl-1 dt-1 l-1 t1)]
          [ft-2->1 (comb-trans dl-2 dt-2 l-1 t4)])
      (lambda (t)
        (cond [(< t t1) (f-1 t)]
              [(< t t2) (ft-1->2 t)]
              [(< t t3) (f-2 (- t t2))]
              ; FIXME we could normalize the transitions so that
              ; they were always normalized to start at t=0, but
              ; it seems more efficient to encode the values in
              ; the constants rather than subtract the time offset
              ; like we have to do for the non-transition periods
              [(< t t4) (ft-2->1 t)]
              [else (f-1 (- t t4))]
              )))))

(define (unitary-pulse
         #:t-2 t-2
         #:t-3 t-3
         #:trans-1 [trans-1 transition-unspecified]
         #:trans-2 [trans-2 transition-unspecified])
  ; t-1 is always 0
  ; t-4 is always 1
  ; l-0 is always 0
  ; l-1 is always 1
  ; s-0 is always (λ (t) 0)
  ; s-1 is always (λ (t) 1)

  ; composition with periodic functions can then proceed
  ; mathematically with the shape defined here
  (values))

(define (norm . vector-values)
  (sqrt (apply + (map sqr vector-values))))

(define (amp-off level-0 level-1)
  "pulse amplitudes are signed"
  (let ([amp (- level-0 level-1)]
        [off level-0])
    (cons amp off)))

(define (arbitrary->unitary pulse-family-function)
  "return a linear normalization of the pulse parameters to
t-4 == 1
level-0 == 0
level-1 == 1

I'm sure there is an edge case with exponential pulses or something.

XXX note that the problem with using something like this is that
there is a risk of losing precision relative to the original input
parameters, further, we already have the prototypical shapes in their
unitary normalized form. This may still be useful for recovering
information about the function at runtime."
  (let* ([h (pulse-family-function 'params)]
         [amplitude-offset (amp-off (hash-ref h '#:level-0) (hash-ref h '#:level-1))]
         [amplitude (car amplitude-offset)]
         [offset (cdr amplitude-offset)]
         ;
         [shift (hash-ref h '#:t-1)]
         [stretch (- (hash-ref h '#:t-4) shift)]
         [t-2 (/ (- (hash-ref h '#:t-2) shift) stretch)]
         [t-3 (/ (- (hash-ref h '#:t-3) shift) stretch)])
    (values (unitary-pulse
             #:t-2 t-2
             #:t-3 t-3)
            amplitude
            offset
            ; FIXME do we normalize to t-1 = 0 or no? that gives us
            ; pulse shape independent of the temporal offset, however
            ; it means that when we scale the pulse we ... I think we
            ; want both, but the default should be for t-1 to be zero,
            ; and the provide the original shift this is related to a
            ; comment about invariants somwhere else in this file
            stretch
            shift)))

(define (cmb-family-pulse
         #:t-1 t1
         #:t-2 t2
         #:t-3 t3
         #:t-4 t4
         #:level-0 [level-0 0]
         #:level-1 [level-1 1]
         #:state-0 [state-0 cmb-constant-level]
         #:state-1 [state-1 (λ (l) (λ (t) l))]
         #:trans-1 [trans-1 transition-unspecified]
         #:trans-2 [trans-2 transition-unspecified])

  ;; levels are set to 0 and 1 by default so that
  ;; the default output can be composed with the usual
  ;; amplitude modifying functions
  ;; because t-1 ... t-4 are concrete times and are not
  ;; given in fractions of a unit epoch, there is no
  ;; easy way to scale those, there was a use case for
  ;; that we could define a variant of this function
  ;; that required the transition times to be on [0,1]
  ;; and then rescaled accordingly, or rather, that
  ;; always set t4 to 1, ... which would allow us to
  ;; translate any pulse into a canonical form along
  ;; with amplitude and phase scaling (stretching?)
  ;; assuming a linear stretching function

  ; XXX how many layers of combinators do we want here?
  ; getting something that can scale in time an level
  ; is the objective, those are the things we want
  ; to specify last, and they should all come together
  ; this is the last stop on the way to getting a
  ; concrete waveform, which means that transitions
  ; and states should be one level above this I think
  ; of course the real issue is that we want to be
  ; able to reparameterize any one thing independent
  ; of all the others after having specified them before
  ; seems like case lambda is probably what we will need ...
  (define current-parameterization-of-f
    (let ([f-1 (state-0 level-0)]
          [f-2 (state-1 level-1)]
          [l-1 level-0]
          ; FIXME dl almost certainly should be calculated to for continuous transitions
          ; with the state function not with the reference level for that function ?
          ; this is something that needs to be clarified, that or all periodic state
          ; functions cannot be arbitrary but must start at zero? seems bad
          ;[dl-1 (dy s1 s2)]
          ;[dl-2 (dy s2 s1)]
          ; XXX need feedback
          )
      (let ([dl-1 (dl-new f-1 f-2 t1)]
            [dl-2 (dl-new f-2 f-1 t3)]
            ;[l-2 (waveform-state-level s2)]
            [dt-1 (- t2 t1)]
            [dt-2 (- t4 t3)])
        (println (list dl-1 dl-2 dt-1 dt-2))
        (let ([ft-1->2 (trans-1 dl-1 dt-1 l-1 t1)]
              [ft-2->1 (trans-2 dl-2 dt-2 l-1 t4)])
          (lambda (t)
            (cond [(< t t1) (f-1 t)]
                  [(< t t2) (ft-1->2 t)]
                  [(< t t3) (f-2 (- t t2))]
                  ; FIXME we could normalize the transitions so that
                  ; they were always normalized to start at t=0, but
                  ; it seems more efficient to encode the values in
                  ; the constants rather than subtract the time offset
                  ; like we have to do for the non-transition periods
                  [(< t t4) (ft-2->1 t)]
                  [else (f-1 (- t t4))]
                  ))))))
  ; unfortunately case-lambda currently does not take keyword
  ; arguments, so we can't do a simple redefinition but we can do it
  ; by having multiple arguments
  (case-lambda
    [() (error 'oops)]
    [(t)
     ; NOTE there is always a default setting
     ; that can be overwritten or specialized
     (current-parameterization-of-f t)]
    [(action . key-value)
     (let ([current (apply hash `(#:t-1 ,t1
                                  #:t-2 ,t2
                                  #:t-3 ,t3
                                  #:t-4 ,t4
                                  #:level-0 ,level-0
                                  #:level-1 ,level-1
                                  #:state-0 ,state-0
                                  #:state-1 ,state-1
                                  #:trans-1 ,trans-1
                                  #:trans-2 ,trans-2))])
       (match action
         ['derive (let ([new-kwargs (hash-union current
                                                (apply hash key-value)
                                                ; last one wins
                                                #:combine/key (λ (k v1 v2) v2)
                                                )])
                    (keyword-apply-hash cmb-family-pulse new-kwargs))]
         ['params current]))]))

(define (keyword-apply-hash f kw-hash)
  (let* ([skeys (sort (hash-keys kw-hash) keyword<?)]
         [svals (map (λ (k) (hash-ref kw-hash k)) skeys)])
    (keyword-apply f skeys svals '())))

(module+ test-cmb-fp
  (define aaa (let ([f (λ (t) 0)])
                (case-lambda
                  [(t) (f t)]
                  [key-value key-value])))
  (aaa '#:a 1 '#:b 2 '#:c 3)

  ; FIXME TODO we can probably actually handle trapezoidal ->
  ; exponental translations by parameterizing tau based on the state
  ; occurance definition for state 2 it is kind of loose, and the
  ; usual criteria for working with exponentials isn the limit is
  ; probably going to cause trouble
  (define lol (cmb-family-pulse
               #:t-1 1
               #:t-2 2
               #:t-3 3
               #:t-4 4
               #:trans-1 transition-linear))
  (define lol2 (lol 'derive
                    '#:t-2 1.5
                    '#:level-1 0.7
                    '#:trans-2 transition-linear))
  (plot (list (axes)
              (function lol 0 5 #:color 8 #:style 0)
              (function lol2 0 5 #:color 8 #:style 1)
              ))
  )

(define s0 (waveform-state 0 (lambda (level) (lambda (t) level))))
(define s1 (waveform-state 1 (lambda (level) (lambda (t) level))))

(module+ test-pulse
  ; TODO in theory we can defer the choice of the state function until
  ; later as well however that makes it hard to distinguish between
  ; states because we never have their full name in the same place at
  ; the same time
  (plot (function (family-pulse s0 s1 1 2 3 4) 0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))
  (plot (function (family-pulse s0 s1 1 2 3 4 make-ft) 0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))
  )

(define (family-trapezoidal s1 s2 t1 t2 t3 t4)
  (family-pulse s1 s2 t1 t2 t3 t4 make-ft))

(define (family-rectangular s1 s2 t12 t34)
  (family-trapezoidal s1 s2 t12 t12 t34 t34))

(define (family-triangular s1 s2 t1 t23 t4)
  (family-trapezoidal s1 s2 t1 t23 t23 t4))

(define (family-ramp s1 s2 t1 t234)
  (family-triangular s1 s2 t1 t234 t234))

#;
(define cmb-constant-level
  ; a state level combinator that returns
  ; a constant value
  (λ (l) (λ (t) l) ))

(define-syntax (define-level-combinator stx)
  "Regularize the creation of state level combinators where `level' will
be bound at runtime."
  (syntax-parse stx
    [(_ body ...)
     ; break hygene so we can use level in the body
     #:with (new-body ...) (datum->syntax #'(body ...) (syntax->datum #'(body ...)))
     #'(λ (level)
         new-body ...)]))

(define-syntax define-cmb-lvl (make-rename-transformer #'define-level-combinator))

(define cmb-constant-level (define-cmb-lvl (λ (t) level)))

(define (cmb-family-trapezoidal t1 t2 t3 t4
                                #:state-0 [state-0 cmb-constant-level]
                                #:state-1 [state-1 (λ (l) (λ (t) l))]
                                )
  (cmb-family-pulse t1 t2 t3 t4
                    #:state-0 state-0
                    #:state-1 state-1))

(module+ test-fam-trap
  ; TODO max over range * 1.5 probably, surely the plot library has this?
  (plot (function (family-trapezoidal s0 s1 1 2 3 4) 0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))
  (plot (function (family-rectangular s0 s1 2 3) 0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))
  (plot (function (family-triangular s0 s1 1 2 3) 0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))
  (plot (function (family-ramp s0 s1 1 4) 0 5 #:y-max 1.5 #:width 3 #:color 8 #:style 0))
  )

(define (state-chain-levels fun . levels) (for/list [(l levels)] (waveform-state l fun)))
; state 2 duration
; epoch duration
;(define (state-chain-duration fun . ) rest) ; this is orthogonal?

(define (epoch-chain #; template-family states duration)
  ; FIXME and this is why we can't use the struct for this because we want to be able to
  ; TODO OR we have to pass in a function that generates states, which probably makes
  ; more sense for now, the only issue is the need to specify the number of epochs in
  ; the chain and which parameter(s) to vary, except that we don't do that here
  ; because this is the copositional interface and the chain doesn't know anything
  ; about the possible parameters for the states
  null
  )

(struct epoch (states transitions duration))

; the fundamental problem when specifying this is that
; we would like to be able to specify 1 or many and have
; the one used across the many by default and everything
; has to be the same length internally
#;
(define (epoch-1 #:fam fam
                 #:fams fams
                 #:dur a
                 #:durs b
                 #:level c
                 #:levels d) #f)

; lexi wrote multimethod and it exists and works but it requires
; that we essentially use structs to box values as types
; all the rest are assumed grouped according to the order ???

#;
(define (echain #:function function
                #:level level
                #:duration duration
                #:transitions transitions
                #:count count
                . vect)
  ; each vect form comes with #:f #:d or #:l at the head
  ; as the parameters d

  )

; the problem with using combinators is that you have to know how to write them
(module+ test-echain
  #;
  (echain #:function constant
          #:duration 3
          #:transition-function family-trapezoidal
          #:transitions [0.5 ; transitions is too narrow if you want to be able to
                         1   ; talk about things like "state 2 duration" but then
                         2   ; how do you keep the generating functions aligned?
                         2.5]
          '[[#:level]
            [1]
            [2]
            [3]
            [4]])
  )

#; ; the problem is with the constructor
(define-generics has-vars
  (has-vars))

#;
(epoch ((for/list ([l (levels)]
                   [f (families)])
          (state f l))))

(module+ test-ec
  (state-chain-levels make-ft 1 2 3 4 5)
  (epoch-chain (state-chain-levels 1 2 3 4 5) )
  )

(define (family-trapezoidal-old s1 s2 t1 t2 t3 t4)
  "asdf"
  ; FIXME ordering restrictions on times
  (let ([f-1 (apply-level s1)]
        [f-2 (apply-level s2)]
        [dy-1 (dy s1 s2)]
        [dy-2 (dy s2 s1)]
        [y-1 (waveform-state-level s1)]
        ;[y-2 (waveform-state-level s2)]
        [dt-1 (- t2 t1)]
        [dt-2 (- t4 t3)])
    (let ([slope-1 (/ dy-1 dt-1)]
          [slope-2 (/ dy-2 dt-2)])
      (let ([intercept-1 (- y-1 (* slope-1 t1))]
            [intercept-2 (- y-1 (* slope-2 t4))])
        (let ([ft-1->2 (lambda (t) (+ (* slope-1 t) intercept-1))]
              [ft-2->1 (lambda (t) (+ (* slope-2 t) intercept-2))])
          (lambda (t)
            (cond [(< t t1) (f-1 t)]
                  [(< t t2) (ft-1->2 t)]
                  [(< t t3) (f-2 (- t t2))]
                  ; FIXME we could normalize the transitions so that
                  ; they were always normalized to start at t=0, but
                  ; it seems more efficient to encode the values in
                  ; the constants rather than subtract the time offset
                  ; like we have to do for the non-transition periods
                  [(< t t4) (ft-2->1 t)]
                  [else (f-1 (- t t4))]
                  )))))))


(define (makepf function
                #:amplitude [a 1] ; *
                #:offset    [o 0] ; +
                #:cycles    [c 1] ; * ; FIXME cycles acts in the opposite manner of amp ...
                #:shift     [s 0] ; + ; FIXME naming this is the phase shift is backward
                ;; cycle, period, and duration depend on the properties of the epoch
                ;; so the atomic cycle count for specifying the periodic function
                ;; will always be 1, cycles is left here for testing purposes
                ;; in reality we should use either cps or just return a combinator
                ;; that takes the cycle time
                ;; #:period [p #f]
                ;; #:frequency [f #f]
                )
  ; cycles period and frequency are all related
  ; I have this sense that for descriptions of
  ; periodic states we need to orthogonlize the
  ; waveform shape and repitition from the duration/frequency
  ; so that I will describe 1 cycle of whatever periodic function
  ; am I creating, and then I will say what the cycle duration is
  ; and that will set the frequency, we could enable authoring of a
  ; an epoch in such a way that frequency and duration could be provided
  ; and we would store that as x repiditions of a block with duration y

  ; only one may be specified at a time
  ; we subtract the shift so that it moves the function in the same
  ; way (logically) as offset so that if I shift the function a quarter
  ; period to the left (this is why we have to force cycles to be 1)
  ; i use shift -0.25, otherwise everything is inverted from the humans perspective

  ;;(λ (x) (+ o (* a (function (* c (- x s)))))) ; pretty sure we don't want c affecting s, extremely confusing and non-orthognoal, and also a basic violation of good mathematical practice with respect to addition vs multiplication
  ; FIXME the way that we handle the s offset needs to be invariant to changes in c
  (λ (x) (+ o (* a (function (- (* c x) s)))))
  )

(module+ test-periodic
  (plot (list (axes)
              (function (makepf sinpi) 0 1 #:color 0)
              (function (makepf sinpi #:amplitude 0.5) 0 1 #:color 1)
              (function (makepf sinpi #:cycles 2) 0 1 #:color 2)
              (function (makepf sinpi #:cycles 0.5) 0 1 #:color 3)
              (function (makepf sinpi #:shift 0.5) 0 1 #:color 4)
              (function (makepf sinpi #:shift 0.25) 0 1 #:color 5)
              (function (makepf sinpi #:amplitude 0.5 #:offset -0.5) 0 1 #:color 6)
              (function (makepf sinpi #:amplitude 0.5 #:offset -0.5 #:shift -0.25)
                        0 1 #:color 7)
              ))

  (plot (list (axes)
              (function (makepf sinpi) 0 1 #:color 0)
              (function (makepf sinpi #:shift 0.5) 0 1 #:color 2)
              (function (makepf sinpi
                                #:amplitude 0.5
                                #:offset -0.5
                                #:shift -0.25  ; FIXME still confused about the -.25 shift when cycle is 2, get it right here otherwise when we compose with epoc duration, problems will occur
                                ;#:shift 0.5
                                #:cycles 2) 0 1 #:color 4)
              (function (makepf sinpi
                                #:amplitude 0.5
                                #:offset -0.5
                                #:cycles 2) 0 1 #:color 8)
              ))

  (require plot/no-gui)
  (parameterize ([line-width 3])
    (plot-file (function (makepf sinpi) 0 1 #:color 8 #:style 0)
               (expand-user-path (string->path "~/ni/dev/nifstd/sinpi.png")))
    (plot (function (makepf sinpi) 0 1 #:color 8 #:style 0)))

  #;
  (plot (list (axes)
              (function (makepf ))
              ))

  )

(module+ test-trap
  (plot (function (makepf constant) 0 1 #:color 8 #:style 0))
  (plot (function (makepf constant #:amplitude 0.5) 0 1 #:color 8 #:style 0))

  (plot (function (makepf linear-transition) -1 2 #:color 8 #:style 0))
  (plot (function (makepf linear-transition #:amplitude 0.5) -1 2 #:color 8 #:style 0))
  (plot (function (makepf linear-transition #:cycles 0) -1 2 #:color 8 #:style 0))

  ; the problem here is that transitions aren't really periodic, so it
  ; is confusing to have to set a high cycle count because you no longer
  ; have control over what you care about, which is exact transition
  ; times and the number of cycles needed to have a 1 bin transition
  ; window will be dependent on the exact rasterization parameters
  (plot (list (axes)
              (function (makepf linear-transition #:cycles 0) -1 2 #:color 8 #:style 0)
              (function (makepf linear-transition #:cycles 1) -1 2 #:color 8 #:style 0)
              (function (makepf linear-transition #:cycles 2) -1 2 #:color 8 #:style 0)
              (function (makepf linear-transition #:cycles 4) -1 2 #:color 8 #:style 0)
              (function (makepf linear-transition #:cycles 8) -1 2 #:color 8 #:style 0)
              (function (makepf linear-transition #:cycles 128) -1 2 #:color 8 #:style 0)))

  (define s0 (waveform-state 0 (lambda (level) (lambda (t) level))))
  (define s1 (waveform-state 1 (lambda (level) (lambda (t) level))))
  ;(define s2 (waveform-state 1 (lambda (level) (lambda (t) (+ level (cospi t))))))
  ; XXX need feedback on the amplitude of the steady state relative to the pulse? or leave it to users?
  (define s2 (waveform-state 0 (lambda (level)
                                 (let ([f (makepf cospi #:shift 0.25 #:amplitude 0.1 #:cycles 12)])
                                   (lambda (t) (+ level (f t)))))))
  #;
  (define s3 (waveform-state 1 (lambda (level)
                                 (let ([f (makepf sinpi #:shift 0.75 #:amplitude 0.1 #:cycles 12)])
                                   (lambda (t) (+ level (f t)))))))
  (define s3 (waveform-state 1 (lambda (level)
                                 (let ([f (makepf cospi #:shift 0.25 #:amplitude 0.1 #:cycles 12)])
                                   (lambda (t) (+ level (f t)))))))
  (plot (function (family-trapezoidal s0 s1 1 2 3 4) 0 5 #:color 8 #:style 0)) ; trap
  (plot (function (family-trapezoidal s0 s1 1 1 2 2) 0 5 #:color 8 #:style 0)) ; rect
  (plot (function (family-trapezoidal s0 s1 1 4 4 4) 0 5 #:color 8 #:style 0)) ; ramp
  (plot (function (family-trapezoidal s0 s1 1 2.5 2.5 4) 0 5 #:color 8 #:style 0)) ; tri

  (plot (function (family-trapezoidal s2 s3 1 2 3 4) 0 5 #:color 8 #:style 0)) ; trap

  )

;;; chirp

(define (make-periodic fun-periodic
                       #:famp [fun-amplitude (λ (t) 1)]
                       #:foff [fun-offset    (λ (t) 0)]
                       #:fcyc [fun-cycles    (λ (t) 1)]
                       #:fshi [fun-shift     (λ (t) 1)])
  ; if you make all of these values functions of t then it is
  ; homogenous, and it is just up to the compiler to be smart about
  ; recognizing contstant functions and replacing them, in fact what
  ; we do here is very close to the example in the documentation on
  ; performance so I would be surprised if these were not optimized
  (λ (t) (+ (fun-offset t)
            (* (fun-amplitude t)
               (fun-periodic (- (* t (fun-cycles t))
                                (fun-shift t)))))))

(module+ test-chirp
  (define line-chirp-1 #f)
  (set! line-chirp-1 (make-periodic sinpi #:fcyc (λ (t) (* 10 t))))
  (define expt-chirp-1 #f)
  (set! expt-chirp-1 (make-periodic sinpi #:fcyc (λ (t) (expt 10 t))))
  (plot (function line-chirp-1 0 1 #:color 8 #:style 0))
  (plot (function expt-chirp-1 0 2 #:color 8 #:style 0)) ; XXX plot has bad rasterization for high frequency
  (plot (function expt-chirp-1 0 1 #:color 8 #:style 0))
  (define wat-1 #f)
  (define beat-1 #f)
  (set! wat-1 (make-periodic sinpi #:fcyc (make-periodic sinpi #:fcyc (λ (t) 2))))
  (set! beat-1 (make-periodic sinpi #:famp (make-periodic sinpi #:fcyc (λ (t) 10))))
  (plot (function beat-1 0 1 #:color 8 #:style 0))
  (define beat-2 #f)
  (set! beat-2 (make-periodic sinpi #:famp (make-periodic sinpi #:fcyc (λ (t) 0.5)) #:fcyc (λ (t) 10)))
  (plot (function beat-2 0 1 #:color 8 #:style 0))

  )

;;; composition

(define (cumsum l)
  (cdr (reverse (foldl (λ (y xs) (cons (+ (car xs) y) xs)) '(0) l)))
  #; ; I was close l vs r issue
  (reverse (foldr (λ (a b) (cons (+ (car a) b) a)) '(0) l)))

(define (waveform-add . functions)
  "Add waveforms together. All functions must take single argument t."
  (λ (t) (apply + (map (λ (f) (f t)) functions))))

(define (waveform-add-curiosity . functions)
  "version of waveform-add implemented via waveform-concat"
  (let ([epoch-durations (for/list ([f functions]) 0)])
    (waveform-concat functions epoch-durations)))

(define (waveform-concat functions epoch-durations)
  "Shift and add. The last epoch duration is ignored but required."
  (let ([shifts (cumsum (cons 0 (reverse (cdr (reverse epoch-durations)))))])
    (λ (t) (apply + (map (λ (f s) (f (- t s))) functions shifts)))))

(define (waveform-compose . functions)
  "This will produce very confusing results if used with most waveforms."
  (λ (t) ((apply compose functions) t)))

(module+ test-compose
  (define f (family-rectangular s0 s1 1 3))
  (define g (family-ramp s0 s1 0 5))
  (define h (waveform-compose f g))
  (define j (waveform-compose g f))
  (plot (function h 0 5 #:color 8 #:style 0))
  (plot (function j 0 5 #:color 8 #:style 0))
  )

(module+ test-add
  (define f (family-rectangular s0 s1 1 3))
  (define g (family-rectangular s0 s1 2 4))
  (define i (family-ramp s0 s1 0 5))
  (define h (waveform-add f g))
  (define j (waveform-add-curiosity f g i))
  (plot (function h 0 5 #:color 8 #:style 0))
  (plot (function j 0 5 #:color 8 #:style 0))
  )

#;
(define (waveform-concat-old . f-end-pairs)
  "This can't take raw functions of time, it has to also take endpoints in time."
  (let ([functions (map car f-end-pairs)]
        [shifts (cumsum (cons 0 (reverse (cdr (map cdr (reverse f-end-pairs))))))])
    (λ (t) (apply + (map (λ (f s) (f (- t s))) functions shifts)))))

(module+ test-concat
  (define f (family-rectangular s0 s1 1 2))
  #;
  (define g (waveform-concat-old (cons f 3) (cons f +inf.0)))
  (define g (waveform-concat
             (list f f)
             (list 3 4)))
  (define h (waveform-add g (family-ramp s0 s1 0 5)))
  (plot (function g 0 10 #:color 8 #:style 0))
  (plot (function h 0 10 #:color 8 #:style 0))
  )
