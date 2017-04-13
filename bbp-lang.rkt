#lang racket/base

(require "bbp-parser.rkt")
(require brag/support)
(require (for-syntax racket/base syntax/parse))

(define (read-syntax path port)
  (define parse-tree (parse path (make-tokenizer port)))
  (define module-datum `(module bbp-mod "bbp-expander.rkt"
                          ,parse-tree))
  (datum->syntax #f module-datum))
(provide read-syntax)

(define-lex-abbrev
  mtypes
  (:or
   "PC"
   "BPC"
   "IPC"
   "NPC"
   "SPC"
   "NTPC"
   "STPC"
   "TTPC"
   "TTPCLB"
   "TTPCEB"
   "TPCLB"
   "TPCEB"
   "UPC"
   "BTC"
   "BPC"
   "ChC"
   "DBC"
   "DAC"
   "HAC"
   "LAC"
   "SAC"
   "MC"
   "NGC"
   "NGCDA"
   "NGCSA"
   "BC"
   "SBC"
   "LBC"
   "NBC"
   "SS"
   "BC"
   "BP"
   "LBC"
   "NBC"
   "SBC"
   )) ; this is infuriating check a macro
(define-lex-abbrev layer (:or "L1" "L2" "L23" "L3" "L4" "L5" "L6"))
(define-lex-abbrev init (:or "b" "c" "d"))
(define-lex-abbrev sust (:or "NAC" "AC" "STUT" "IR"))
(define-lex-abbrev species (:or "Rat" "Mouse"))
(define-lex-abbrev region (:or "S1"))
(define-lex-abbrev projection (:or "L1P" "L3P" "L4P")) ; not wokring :/

(define (make-tokenizer port)
  (define (next-token)
    (define bbp-lexer
      (lexer
       [(eof) eof]
       [layer (token 'LAYER lexeme)]
       [mtypes (token 'M-TYPE lexeme)]
       [init (token 'INIT lexeme)]
       [sust (token 'SUST lexeme)]
       [species (token 'SPECIES lexeme)]
       [region (token 'REGION lexeme)]
       [projection (token 'PROJECTION lexeme)] ; a problem
       ["_" (token 'UNDERSCORE)]
       ))
    (bbp-lexer port))
  next-token)

(apply-tokenizer-maker make-tokenizer "L1_PC")
(parse-to-datum (apply-tokenizer-maker make-tokenizer "L1_PC"))
(parse-to-datum (apply-tokenizer-maker make-tokenizer "L23_PC"))
(parse-to-datum (apply-tokenizer-maker make-tokenizer "PC"))
(parse-to-datum (apply-tokenizer-maker make-tokenizer "Rat_S1_L4_PC_cAC_L3P"))
