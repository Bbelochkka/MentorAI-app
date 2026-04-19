--
-- PostgreSQL database dump
--

\restrict l0LgGfq1QG1QAxzeZkUmGInaiduugR99hHabsPC4o8KyajAGy2aLL6L99egdOQh

-- Dumped from database version 17.9
-- Dumped by pg_dump version 17.9

-- Started on 2026-04-05 21:52:45

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 272 (class 1259 OID 30321)
-- Name: activity_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_events (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    user_id bigint,
    event_type character varying(100) NOT NULL,
    entity_type character varying(100) NOT NULL,
    entity_id bigint,
    event_time timestamp with time zone DEFAULT now() NOT NULL,
    payload_json jsonb
);


ALTER TABLE public.activity_events OWNER TO postgres;

--
-- TOC entry 271 (class 1259 OID 30320)
-- Name: activity_events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.activity_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.activity_events_id_seq OWNER TO postgres;

--
-- TOC entry 5378 (class 0 OID 0)
-- Dependencies: 271
-- Name: activity_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.activity_events_id_seq OWNED BY public.activity_events.id;


--
-- TOC entry 268 (class 1259 OID 30269)
-- Name: bot_queries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bot_queries (
    id bigint NOT NULL,
    chat_session_id bigint,
    user_id bigint NOT NULL,
    company_id bigint NOT NULL,
    training_session_id bigint,
    query_text text NOT NULL,
    answer_text text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.bot_queries OWNER TO postgres;

--
-- TOC entry 267 (class 1259 OID 30268)
-- Name: bot_queries_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.bot_queries_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bot_queries_id_seq OWNER TO postgres;

--
-- TOC entry 5379 (class 0 OID 0)
-- Dependencies: 267
-- Name: bot_queries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.bot_queries_id_seq OWNED BY public.bot_queries.id;


--
-- TOC entry 270 (class 1259 OID 30299)
-- Name: bot_query_sources; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bot_query_sources (
    id bigint NOT NULL,
    bot_query_id bigint NOT NULL,
    document_id bigint NOT NULL,
    chunk_id bigint,
    relevance_score numeric(6,4)
);


ALTER TABLE public.bot_query_sources OWNER TO postgres;

--
-- TOC entry 269 (class 1259 OID 30298)
-- Name: bot_query_sources_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.bot_query_sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bot_query_sources_id_seq OWNER TO postgres;

--
-- TOC entry 5380 (class 0 OID 0)
-- Dependencies: 269
-- Name: bot_query_sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.bot_query_sources_id_seq OWNED BY public.bot_query_sources.id;


--
-- TOC entry 266 (class 1259 OID 30256)
-- Name: chat_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_sessions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    closed_at timestamp with time zone
);


ALTER TABLE public.chat_sessions OWNER TO postgres;

--
-- TOC entry 265 (class 1259 OID 30255)
-- Name: chat_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chat_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_sessions_id_seq OWNER TO postgres;

--
-- TOC entry 5381 (class 0 OID 0)
-- Dependencies: 265
-- Name: chat_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chat_sessions_id_seq OWNED BY public.chat_sessions.id;


--
-- TOC entry 220 (class 1259 OID 29736)
-- Name: companies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.companies (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.companies OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 29735)
-- Name: companies_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.companies_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.companies_id_seq OWNER TO postgres;

--
-- TOC entry 5382 (class 0 OID 0)
-- Dependencies: 219
-- Name: companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.companies_id_seq OWNED BY public.companies.id;


--
-- TOC entry 238 (class 1259 OID 29925)
-- Name: course_document_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_document_links (
    id bigint NOT NULL,
    course_id bigint NOT NULL,
    document_id bigint NOT NULL
);


ALTER TABLE public.course_document_links OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 29924)
-- Name: course_document_links_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.course_document_links_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.course_document_links_id_seq OWNER TO postgres;

--
-- TOC entry 5383 (class 0 OID 0)
-- Dependencies: 237
-- Name: course_document_links_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.course_document_links_id_seq OWNED BY public.course_document_links.id;


--
-- TOC entry 234 (class 1259 OID 29892)
-- Name: course_modules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_modules (
    id bigint NOT NULL,
    course_version_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    sort_order integer DEFAULT 1 NOT NULL
);


ALTER TABLE public.course_modules OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 29891)
-- Name: course_modules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.course_modules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.course_modules_id_seq OWNER TO postgres;

--
-- TOC entry 5384 (class 0 OID 0)
-- Dependencies: 233
-- Name: course_modules_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.course_modules_id_seq OWNED BY public.course_modules.id;


--
-- TOC entry 236 (class 1259 OID 29905)
-- Name: course_topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_topics (
    id bigint NOT NULL,
    module_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    content text,
    source_chunk_id bigint,
    sort_order integer DEFAULT 1 NOT NULL
);


ALTER TABLE public.course_topics OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 29904)
-- Name: course_topics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.course_topics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.course_topics_id_seq OWNER TO postgres;

--
-- TOC entry 5385 (class 0 OID 0)
-- Dependencies: 235
-- Name: course_topics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.course_topics_id_seq OWNED BY public.course_topics.id;


--
-- TOC entry 232 (class 1259 OID 29858)
-- Name: course_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.course_versions (
    id bigint NOT NULL,
    course_id bigint NOT NULL,
    version_number integer NOT NULL,
    generated_from_document_id bigint,
    created_by bigint,
    approved_by bigint,
    approved_at timestamp with time zone,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_course_versions_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'published'::character varying, 'archived'::character varying])::text[])))
);


ALTER TABLE public.course_versions OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 29857)
-- Name: course_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.course_versions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.course_versions_id_seq OWNER TO postgres;

--
-- TOC entry 5386 (class 0 OID 0)
-- Dependencies: 231
-- Name: course_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.course_versions_id_seq OWNED BY public.course_versions.id;


--
-- TOC entry 230 (class 1259 OID 29834)
-- Name: courses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.courses (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    created_by bigint,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    current_version_no integer DEFAULT 1 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_courses_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'published'::character varying, 'archived'::character varying])::text[])))
);


ALTER TABLE public.courses OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 29833)
-- Name: courses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.courses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.courses_id_seq OWNER TO postgres;

--
-- TOC entry 5387 (class 0 OID 0)
-- Dependencies: 229
-- Name: courses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.courses_id_seq OWNED BY public.courses.id;


--
-- TOC entry 260 (class 1259 OID 30192)
-- Name: dialog_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dialog_messages (
    id bigint NOT NULL,
    session_id bigint NOT NULL,
    step_id bigint,
    sender_type character varying(20) NOT NULL,
    message_text text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_dialog_messages_sender_type CHECK (((sender_type)::text = ANY ((ARRAY['user'::character varying, 'virtual_client'::character varying, 'system'::character varying])::text[])))
);


ALTER TABLE public.dialog_messages OWNER TO postgres;

--
-- TOC entry 259 (class 1259 OID 30191)
-- Name: dialog_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dialog_messages_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dialog_messages_id_seq OWNER TO postgres;

--
-- TOC entry 5388 (class 0 OID 0)
-- Dependencies: 259
-- Name: dialog_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dialog_messages_id_seq OWNED BY public.dialog_messages.id;


--
-- TOC entry 280 (class 1259 OID 30406)
-- Name: dialog_stage_mart; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dialog_stage_mart (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    user_id bigint NOT NULL,
    scenario_id bigint NOT NULL,
    stage_type character varying(30) NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    avg_score numeric(5,2) DEFAULT 0 NOT NULL,
    error_count integer DEFAULT 0 NOT NULL,
    success_rate numeric(5,2) DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_dialog_stage_mart_type CHECK (((stage_type)::text = ANY ((ARRAY['intro'::character varying, 'need_discovery'::character varying, 'presentation'::character varying, 'objection'::character varying, 'closing'::character varying, 'custom'::character varying])::text[])))
);


ALTER TABLE public.dialog_stage_mart OWNER TO postgres;

--
-- TOC entry 279 (class 1259 OID 30405)
-- Name: dialog_stage_mart_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dialog_stage_mart_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dialog_stage_mart_id_seq OWNER TO postgres;

--
-- TOC entry 5389 (class 0 OID 0)
-- Dependencies: 279
-- Name: dialog_stage_mart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.dialog_stage_mart_id_seq OWNED BY public.dialog_stage_mart.id;


--
-- TOC entry 228 (class 1259 OID 29817)
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.document_chunks (
    id bigint NOT NULL,
    document_id bigint NOT NULL,
    chunk_index integer NOT NULL,
    chunk_text text NOT NULL,
    embedding_ref text,
    page_num integer,
    source_position character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.document_chunks OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 29816)
-- Name: document_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.document_chunks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.document_chunks_id_seq OWNER TO postgres;

--
-- TOC entry 5390 (class 0 OID 0)
-- Dependencies: 227
-- Name: document_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.document_chunks_id_seq OWNED BY public.document_chunks.id;


--
-- TOC entry 226 (class 1259 OID 29794)
-- Name: documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.documents (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    uploaded_by bigint,
    title character varying(255) NOT NULL,
    file_name character varying(255) NOT NULL,
    file_type character varying(20) NOT NULL,
    file_path text NOT NULL,
    raw_text text,
    status character varying(20) DEFAULT 'uploaded'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_documents_file_type CHECK (((file_type)::text = ANY ((ARRAY['pdf'::character varying, 'docx'::character varying, 'txt'::character varying, 'other'::character varying])::text[]))),
    CONSTRAINT chk_documents_status CHECK (((status)::text = ANY ((ARRAY['uploaded'::character varying, 'processing'::character varying, 'processed'::character varying, 'failed'::character varying, 'archived'::character varying])::text[])))
);


ALTER TABLE public.documents OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 29793)
-- Name: documents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.documents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.documents_id_seq OWNER TO postgres;

--
-- TOC entry 5391 (class 0 OID 0)
-- Dependencies: 225
-- Name: documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.documents_id_seq OWNED BY public.documents.id;


--
-- TOC entry 274 (class 1259 OID 30341)
-- Name: employee_progress_mart; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employee_progress_mart (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    user_id bigint NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    adaptation_index numeric(5,2) DEFAULT 0 NOT NULL,
    course_progress numeric(5,2) DEFAULT 0 NOT NULL,
    test_progress numeric(5,2) DEFAULT 0 NOT NULL,
    dialog_progress numeric(5,2) DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.employee_progress_mart OWNER TO postgres;

--
-- TOC entry 273 (class 1259 OID 30340)
-- Name: employee_progress_mart_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.employee_progress_mart_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.employee_progress_mart_id_seq OWNER TO postgres;

--
-- TOC entry 5392 (class 0 OID 0)
-- Dependencies: 273
-- Name: employee_progress_mart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.employee_progress_mart_id_seq OWNED BY public.employee_progress_mart.id;


--
-- TOC entry 276 (class 1259 OID 30365)
-- Name: group_progress_mart; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.group_progress_mart (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    team_id bigint,
    period_start date NOT NULL,
    period_end date NOT NULL,
    avg_adaptation_index numeric(5,2) DEFAULT 0 NOT NULL,
    risk_count integer DEFAULT 0 NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.group_progress_mart OWNER TO postgres;

--
-- TOC entry 275 (class 1259 OID 30364)
-- Name: group_progress_mart_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.group_progress_mart_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.group_progress_mart_id_seq OWNER TO postgres;

--
-- TOC entry 5393 (class 0 OID 0)
-- Dependencies: 275
-- Name: group_progress_mart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.group_progress_mart_id_seq OWNED BY public.group_progress_mart.id;


--
-- TOC entry 246 (class 1259 OID 30027)
-- Name: question_options; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.question_options (
    id bigint NOT NULL,
    question_id bigint NOT NULL,
    option_text text NOT NULL,
    is_correct boolean DEFAULT false NOT NULL,
    sort_order integer DEFAULT 1 NOT NULL
);


ALTER TABLE public.question_options OWNER TO postgres;

--
-- TOC entry 245 (class 1259 OID 30026)
-- Name: question_options_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.question_options_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.question_options_id_seq OWNER TO postgres;

--
-- TOC entry 5394 (class 0 OID 0)
-- Dependencies: 245
-- Name: question_options_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.question_options_id_seq OWNED BY public.question_options.id;


--
-- TOC entry 250 (class 1259 OID 30072)
-- Name: question_responses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.question_responses (
    id bigint NOT NULL,
    attempt_id bigint NOT NULL,
    question_id bigint NOT NULL,
    selected_option_id bigint,
    answer_text text,
    is_correct boolean,
    earned_score numeric(8,2) DEFAULT 0 NOT NULL,
    responded_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.question_responses OWNER TO postgres;

--
-- TOC entry 249 (class 1259 OID 30071)
-- Name: question_responses_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.question_responses_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.question_responses_id_seq OWNER TO postgres;

--
-- TOC entry 5395 (class 0 OID 0)
-- Dependencies: 249
-- Name: question_responses_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.question_responses_id_seq OWNED BY public.question_responses.id;


--
-- TOC entry 244 (class 1259 OID 30005)
-- Name: questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questions (
    id bigint NOT NULL,
    test_version_id bigint NOT NULL,
    topic_id bigint,
    question_text text NOT NULL,
    question_type character varying(20) NOT NULL,
    weight numeric(8,2) DEFAULT 1.00 NOT NULL,
    sort_order integer DEFAULT 1 NOT NULL,
    CONSTRAINT chk_questions_type CHECK (((question_type)::text = ANY ((ARRAY['single_choice'::character varying, 'multiple_choice'::character varying, 'open_text'::character varying])::text[])))
);


ALTER TABLE public.questions OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 30004)
-- Name: questions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questions_id_seq OWNER TO postgres;

--
-- TOC entry 5396 (class 0 OID 0)
-- Dependencies: 243
-- Name: questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questions_id_seq OWNED BY public.questions.id;


--
-- TOC entry 218 (class 1259 OID 29726)
-- Name: roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roles (
    id smallint NOT NULL,
    code character varying(20) NOT NULL,
    CONSTRAINT chk_roles_code CHECK (((code)::text = ANY ((ARRAY['employer'::character varying, 'manager'::character varying, 'admin'::character varying])::text[])))
);


ALTER TABLE public.roles OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 29725)
-- Name: roles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.roles_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.roles_id_seq OWNER TO postgres;

--
-- TOC entry 5397 (class 0 OID 0)
-- Dependencies: 217
-- Name: roles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.roles_id_seq OWNED BY public.roles.id;


--
-- TOC entry 254 (class 1259 OID 30123)
-- Name: scenario_steps; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scenario_steps (
    id bigint NOT NULL,
    scenario_id bigint NOT NULL,
    step_code character varying(100) NOT NULL,
    step_name character varying(255) NOT NULL,
    stage_type character varying(30) NOT NULL,
    expected_result text,
    sort_order integer DEFAULT 1 NOT NULL,
    CONSTRAINT chk_scenario_steps_stage_type CHECK (((stage_type)::text = ANY ((ARRAY['intro'::character varying, 'need_discovery'::character varying, 'presentation'::character varying, 'objection'::character varying, 'closing'::character varying, 'custom'::character varying])::text[])))
);


ALTER TABLE public.scenario_steps OWNER TO postgres;

--
-- TOC entry 253 (class 1259 OID 30122)
-- Name: scenario_steps_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.scenario_steps_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.scenario_steps_id_seq OWNER TO postgres;

--
-- TOC entry 5398 (class 0 OID 0)
-- Dependencies: 253
-- Name: scenario_steps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.scenario_steps_id_seq OWNED BY public.scenario_steps.id;


--
-- TOC entry 256 (class 1259 OID 30143)
-- Name: scenario_transitions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scenario_transitions (
    id bigint NOT NULL,
    scenario_id bigint NOT NULL,
    from_step_id bigint NOT NULL,
    to_step_id bigint NOT NULL,
    transition_condition text,
    transition_type character varying(20) DEFAULT 'next'::character varying NOT NULL,
    CONSTRAINT chk_scenario_transitions_type CHECK (((transition_type)::text = ANY ((ARRAY['next'::character varying, 'success'::character varying, 'failure'::character varying, 'branch'::character varying])::text[])))
);


ALTER TABLE public.scenario_transitions OWNER TO postgres;

--
-- TOC entry 255 (class 1259 OID 30142)
-- Name: scenario_transitions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.scenario_transitions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.scenario_transitions_id_seq OWNER TO postgres;

--
-- TOC entry 5399 (class 0 OID 0)
-- Dependencies: 255
-- Name: scenario_transitions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.scenario_transitions_id_seq OWNED BY public.scenario_transitions.id;


--
-- TOC entry 252 (class 1259 OID 30098)
-- Name: scenarios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scenarios (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    title character varying(255) NOT NULL,
    scenario_type character varying(30) NOT NULL,
    description text,
    difficulty character varying(10) DEFAULT 'medium'::character varying NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    created_by bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_scenarios_difficulty CHECK (((difficulty)::text = ANY ((ARRAY['easy'::character varying, 'medium'::character varying, 'hard'::character varying])::text[]))),
    CONSTRAINT chk_scenarios_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT chk_scenarios_type CHECK (((scenario_type)::text = ANY ((ARRAY['cold_call'::character varying, 'objection_handling'::character varying, 'closing'::character varying, 'custom'::character varying])::text[])))
);


ALTER TABLE public.scenarios OWNER TO postgres;

--
-- TOC entry 251 (class 1259 OID 30097)
-- Name: scenarios_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.scenarios_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.scenarios_id_seq OWNER TO postgres;

--
-- TOC entry 5400 (class 0 OID 0)
-- Dependencies: 251
-- Name: scenarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.scenarios_id_seq OWNED BY public.scenarios.id;


--
-- TOC entry 264 (class 1259 OID 30238)
-- Name: session_results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.session_results (
    id bigint NOT NULL,
    session_id bigint NOT NULL,
    total_score numeric(8,2) DEFAULT 0 NOT NULL,
    strong_sides text,
    weak_sides text,
    missed_steps text,
    recommendations text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.session_results OWNER TO postgres;

--
-- TOC entry 263 (class 1259 OID 30237)
-- Name: session_results_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.session_results_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.session_results_id_seq OWNER TO postgres;

--
-- TOC entry 5401 (class 0 OID 0)
-- Dependencies: 263
-- Name: session_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.session_results_id_seq OWNED BY public.session_results.id;


--
-- TOC entry 262 (class 1259 OID 30213)
-- Name: step_evaluations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.step_evaluations (
    id bigint NOT NULL,
    session_id bigint NOT NULL,
    step_id bigint NOT NULL,
    score numeric(8,2) DEFAULT 0 NOT NULL,
    comment text,
    funnel_stage_score numeric(8,2) DEFAULT 0 NOT NULL,
    product_score numeric(8,2) DEFAULT 0 NOT NULL,
    objection_score numeric(8,2) DEFAULT 0 NOT NULL,
    script_score numeric(8,2) DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.step_evaluations OWNER TO postgres;

--
-- TOC entry 261 (class 1259 OID 30212)
-- Name: step_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.step_evaluations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.step_evaluations_id_seq OWNER TO postgres;

--
-- TOC entry 5402 (class 0 OID 0)
-- Dependencies: 261
-- Name: step_evaluations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.step_evaluations_id_seq OWNED BY public.step_evaluations.id;


--
-- TOC entry 222 (class 1259 OID 29746)
-- Name: teams; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teams (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    name character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    manager_user_id bigint
);


ALTER TABLE public.teams OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 29745)
-- Name: teams_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.teams_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.teams_id_seq OWNER TO postgres;

--
-- TOC entry 5403 (class 0 OID 0)
-- Dependencies: 221
-- Name: teams_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.teams_id_seq OWNED BY public.teams.id;


--
-- TOC entry 248 (class 1259 OID 30043)
-- Name: test_attempts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.test_attempts (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    test_id bigint NOT NULL,
    test_version_id bigint NOT NULL,
    attempt_no integer NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    score numeric(8,2) DEFAULT 0 NOT NULL,
    percent numeric(5,2) DEFAULT 0 NOT NULL,
    status character varying(20) DEFAULT 'started'::character varying NOT NULL,
    CONSTRAINT chk_test_attempts_status CHECK (((status)::text = ANY ((ARRAY['started'::character varying, 'completed'::character varying, 'abandoned'::character varying])::text[])))
);


ALTER TABLE public.test_attempts OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 30042)
-- Name: test_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.test_attempts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.test_attempts_id_seq OWNER TO postgres;

--
-- TOC entry 5404 (class 0 OID 0)
-- Dependencies: 247
-- Name: test_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.test_attempts_id_seq OWNED BY public.test_attempts.id;


--
-- TOC entry 242 (class 1259 OID 29978)
-- Name: test_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.test_versions (
    id bigint NOT NULL,
    test_id bigint NOT NULL,
    version_number integer NOT NULL,
    created_by bigint,
    approved_by bigint,
    approved_at timestamp with time zone,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_test_versions_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'published'::character varying, 'archived'::character varying])::text[])))
);


ALTER TABLE public.test_versions OWNER TO postgres;

--
-- TOC entry 241 (class 1259 OID 29977)
-- Name: test_versions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.test_versions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.test_versions_id_seq OWNER TO postgres;

--
-- TOC entry 5405 (class 0 OID 0)
-- Dependencies: 241
-- Name: test_versions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.test_versions_id_seq OWNED BY public.test_versions.id;


--
-- TOC entry 240 (class 1259 OID 29944)
-- Name: tests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tests (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    course_id bigint NOT NULL,
    topic_id bigint,
    title character varying(255) NOT NULL,
    test_type character varying(20) DEFAULT 'course'::character varying NOT NULL,
    status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    current_version_no integer DEFAULT 1 NOT NULL,
    created_by bigint,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT chk_tests_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'approved'::character varying, 'published'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT chk_tests_type CHECK (((test_type)::text = ANY ((ARRAY['course'::character varying, 'topic'::character varying, 'mini'::character varying, 'final'::character varying])::text[])))
);


ALTER TABLE public.tests OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 29943)
-- Name: tests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.tests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tests_id_seq OWNER TO postgres;

--
-- TOC entry 5406 (class 0 OID 0)
-- Dependencies: 239
-- Name: tests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.tests_id_seq OWNED BY public.tests.id;


--
-- TOC entry 278 (class 1259 OID 30387)
-- Name: topic_error_mart; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topic_error_mart (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    topic_id bigint NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    error_count integer DEFAULT 0 NOT NULL,
    avg_score numeric(5,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.topic_error_mart OWNER TO postgres;

--
-- TOC entry 277 (class 1259 OID 30386)
-- Name: topic_error_mart_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.topic_error_mart_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topic_error_mart_id_seq OWNER TO postgres;

--
-- TOC entry 5407 (class 0 OID 0)
-- Dependencies: 277
-- Name: topic_error_mart_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.topic_error_mart_id_seq OWNED BY public.topic_error_mart.id;


--
-- TOC entry 258 (class 1259 OID 30169)
-- Name: training_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.training_sessions (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    scenario_id bigint NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    mode character varying(20) DEFAULT 'training'::character varying NOT NULL,
    status character varying(20) DEFAULT 'started'::character varying NOT NULL,
    final_score numeric(8,2) DEFAULT 0 NOT NULL,
    CONSTRAINT chk_training_sessions_mode CHECK (((mode)::text = ANY ((ARRAY['training'::character varying, 'exam'::character varying])::text[]))),
    CONSTRAINT chk_training_sessions_status CHECK (((status)::text = ANY ((ARRAY['started'::character varying, 'completed'::character varying, 'abandoned'::character varying])::text[])))
);


ALTER TABLE public.training_sessions OWNER TO postgres;

--
-- TOC entry 257 (class 1259 OID 30168)
-- Name: training_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.training_sessions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.training_sessions_id_seq OWNER TO postgres;

--
-- TOC entry 5408 (class 0 OID 0)
-- Dependencies: 257
-- Name: training_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.training_sessions_id_seq OWNED BY public.training_sessions.id;


--
-- TOC entry 224 (class 1259 OID 29761)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id bigint NOT NULL,
    company_id bigint NOT NULL,
    team_id bigint,
    role_id smallint NOT NULL,
    full_name character varying(255) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 29760)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 5409 (class 0 OID 0)
-- Dependencies: 223
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 4929 (class 2604 OID 30324)
-- Name: activity_events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_events ALTER COLUMN id SET DEFAULT nextval('public.activity_events_id_seq'::regclass);


--
-- TOC entry 4926 (class 2604 OID 30272)
-- Name: bot_queries id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_queries ALTER COLUMN id SET DEFAULT nextval('public.bot_queries_id_seq'::regclass);


--
-- TOC entry 4928 (class 2604 OID 30302)
-- Name: bot_query_sources id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_query_sources ALTER COLUMN id SET DEFAULT nextval('public.bot_query_sources_id_seq'::regclass);


--
-- TOC entry 4924 (class 2604 OID 30259)
-- Name: chat_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions ALTER COLUMN id SET DEFAULT nextval('public.chat_sessions_id_seq'::regclass);


--
-- TOC entry 4851 (class 2604 OID 29739)
-- Name: companies id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies ALTER COLUMN id SET DEFAULT nextval('public.companies_id_seq'::regclass);


--
-- TOC entry 4875 (class 2604 OID 29928)
-- Name: course_document_links id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_document_links ALTER COLUMN id SET DEFAULT nextval('public.course_document_links_id_seq'::regclass);


--
-- TOC entry 4871 (class 2604 OID 29895)
-- Name: course_modules id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_modules ALTER COLUMN id SET DEFAULT nextval('public.course_modules_id_seq'::regclass);


--
-- TOC entry 4873 (class 2604 OID 29908)
-- Name: course_topics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_topics ALTER COLUMN id SET DEFAULT nextval('public.course_topics_id_seq'::regclass);


--
-- TOC entry 4868 (class 2604 OID 29861)
-- Name: course_versions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_versions ALTER COLUMN id SET DEFAULT nextval('public.course_versions_id_seq'::regclass);


--
-- TOC entry 4863 (class 2604 OID 29837)
-- Name: courses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.courses ALTER COLUMN id SET DEFAULT nextval('public.courses_id_seq'::regclass);


--
-- TOC entry 4912 (class 2604 OID 30195)
-- Name: dialog_messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_messages ALTER COLUMN id SET DEFAULT nextval('public.dialog_messages_id_seq'::regclass);


--
-- TOC entry 4944 (class 2604 OID 30409)
-- Name: dialog_stage_mart id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_stage_mart ALTER COLUMN id SET DEFAULT nextval('public.dialog_stage_mart_id_seq'::regclass);


--
-- TOC entry 4861 (class 2604 OID 29820)
-- Name: document_chunks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks ALTER COLUMN id SET DEFAULT nextval('public.document_chunks_id_seq'::regclass);


--
-- TOC entry 4858 (class 2604 OID 29797)
-- Name: documents id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents ALTER COLUMN id SET DEFAULT nextval('public.documents_id_seq'::regclass);


--
-- TOC entry 4931 (class 2604 OID 30344)
-- Name: employee_progress_mart id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_progress_mart ALTER COLUMN id SET DEFAULT nextval('public.employee_progress_mart_id_seq'::regclass);


--
-- TOC entry 4937 (class 2604 OID 30368)
-- Name: group_progress_mart id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_progress_mart ALTER COLUMN id SET DEFAULT nextval('public.group_progress_mart_id_seq'::regclass);


--
-- TOC entry 4888 (class 2604 OID 30030)
-- Name: question_options id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_options ALTER COLUMN id SET DEFAULT nextval('public.question_options_id_seq'::regclass);


--
-- TOC entry 4896 (class 2604 OID 30075)
-- Name: question_responses id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_responses ALTER COLUMN id SET DEFAULT nextval('public.question_responses_id_seq'::regclass);


--
-- TOC entry 4885 (class 2604 OID 30008)
-- Name: questions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions ALTER COLUMN id SET DEFAULT nextval('public.questions_id_seq'::regclass);


--
-- TOC entry 4850 (class 2604 OID 29729)
-- Name: roles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles ALTER COLUMN id SET DEFAULT nextval('public.roles_id_seq'::regclass);


--
-- TOC entry 4903 (class 2604 OID 30126)
-- Name: scenario_steps id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_steps ALTER COLUMN id SET DEFAULT nextval('public.scenario_steps_id_seq'::regclass);


--
-- TOC entry 4905 (class 2604 OID 30146)
-- Name: scenario_transitions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_transitions ALTER COLUMN id SET DEFAULT nextval('public.scenario_transitions_id_seq'::regclass);


--
-- TOC entry 4899 (class 2604 OID 30101)
-- Name: scenarios id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenarios ALTER COLUMN id SET DEFAULT nextval('public.scenarios_id_seq'::regclass);


--
-- TOC entry 4921 (class 2604 OID 30241)
-- Name: session_results id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_results ALTER COLUMN id SET DEFAULT nextval('public.session_results_id_seq'::regclass);


--
-- TOC entry 4914 (class 2604 OID 30216)
-- Name: step_evaluations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.step_evaluations ALTER COLUMN id SET DEFAULT nextval('public.step_evaluations_id_seq'::regclass);


--
-- TOC entry 4853 (class 2604 OID 29749)
-- Name: teams id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams ALTER COLUMN id SET DEFAULT nextval('public.teams_id_seq'::regclass);


--
-- TOC entry 4891 (class 2604 OID 30046)
-- Name: test_attempts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_attempts ALTER COLUMN id SET DEFAULT nextval('public.test_attempts_id_seq'::regclass);


--
-- TOC entry 4882 (class 2604 OID 29981)
-- Name: test_versions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_versions ALTER COLUMN id SET DEFAULT nextval('public.test_versions_id_seq'::regclass);


--
-- TOC entry 4876 (class 2604 OID 29947)
-- Name: tests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tests ALTER COLUMN id SET DEFAULT nextval('public.tests_id_seq'::regclass);


--
-- TOC entry 4941 (class 2604 OID 30390)
-- Name: topic_error_mart id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic_error_mart ALTER COLUMN id SET DEFAULT nextval('public.topic_error_mart_id_seq'::regclass);


--
-- TOC entry 4907 (class 2604 OID 30172)
-- Name: training_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.training_sessions ALTER COLUMN id SET DEFAULT nextval('public.training_sessions_id_seq'::regclass);


--
-- TOC entry 4855 (class 2604 OID 29764)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 5364 (class 0 OID 30321)
-- Dependencies: 272
-- Data for Name: activity_events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.activity_events (id, company_id, user_id, event_type, entity_type, entity_id, event_time, payload_json) FROM stdin;
\.


--
-- TOC entry 5360 (class 0 OID 30269)
-- Dependencies: 268
-- Data for Name: bot_queries; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bot_queries (id, chat_session_id, user_id, company_id, training_session_id, query_text, answer_text, created_at) FROM stdin;
\.


--
-- TOC entry 5362 (class 0 OID 30299)
-- Dependencies: 270
-- Data for Name: bot_query_sources; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.bot_query_sources (id, bot_query_id, document_id, chunk_id, relevance_score) FROM stdin;
\.


--
-- TOC entry 5358 (class 0 OID 30256)
-- Dependencies: 266
-- Data for Name: chat_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.chat_sessions (id, user_id, started_at, closed_at) FROM stdin;
\.


--
-- TOC entry 5312 (class 0 OID 29736)
-- Dependencies: 220
-- Data for Name: companies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.companies (id, name, created_at) FROM stdin;
\.


--
-- TOC entry 5330 (class 0 OID 29925)
-- Dependencies: 238
-- Data for Name: course_document_links; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_document_links (id, course_id, document_id) FROM stdin;
\.


--
-- TOC entry 5326 (class 0 OID 29892)
-- Dependencies: 234
-- Data for Name: course_modules; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_modules (id, course_version_id, title, sort_order) FROM stdin;
\.


--
-- TOC entry 5328 (class 0 OID 29905)
-- Dependencies: 236
-- Data for Name: course_topics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_topics (id, module_id, title, content, source_chunk_id, sort_order) FROM stdin;
\.


--
-- TOC entry 5324 (class 0 OID 29858)
-- Dependencies: 232
-- Data for Name: course_versions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.course_versions (id, course_id, version_number, generated_from_document_id, created_by, approved_by, approved_at, status, notes, created_at) FROM stdin;
\.


--
-- TOC entry 5322 (class 0 OID 29834)
-- Dependencies: 230
-- Data for Name: courses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.courses (id, company_id, title, description, created_by, status, current_version_no, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5352 (class 0 OID 30192)
-- Dependencies: 260
-- Data for Name: dialog_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dialog_messages (id, session_id, step_id, sender_type, message_text, created_at) FROM stdin;
\.


--
-- TOC entry 5372 (class 0 OID 30406)
-- Dependencies: 280
-- Data for Name: dialog_stage_mart; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.dialog_stage_mart (id, company_id, user_id, scenario_id, stage_type, period_start, period_end, avg_score, error_count, success_rate, updated_at) FROM stdin;
\.


--
-- TOC entry 5320 (class 0 OID 29817)
-- Dependencies: 228
-- Data for Name: document_chunks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.document_chunks (id, document_id, chunk_index, chunk_text, embedding_ref, page_num, source_position, created_at) FROM stdin;
\.


--
-- TOC entry 5318 (class 0 OID 29794)
-- Dependencies: 226
-- Data for Name: documents; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.documents (id, company_id, uploaded_by, title, file_name, file_type, file_path, raw_text, status, created_at) FROM stdin;
\.


--
-- TOC entry 5366 (class 0 OID 30341)
-- Dependencies: 274
-- Data for Name: employee_progress_mart; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employee_progress_mart (id, company_id, user_id, period_start, period_end, adaptation_index, course_progress, test_progress, dialog_progress, updated_at) FROM stdin;
\.


--
-- TOC entry 5368 (class 0 OID 30365)
-- Dependencies: 276
-- Data for Name: group_progress_mart; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.group_progress_mart (id, company_id, team_id, period_start, period_end, avg_adaptation_index, risk_count, updated_at) FROM stdin;
\.


--
-- TOC entry 5338 (class 0 OID 30027)
-- Dependencies: 246
-- Data for Name: question_options; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.question_options (id, question_id, option_text, is_correct, sort_order) FROM stdin;
\.


--
-- TOC entry 5342 (class 0 OID 30072)
-- Dependencies: 250
-- Data for Name: question_responses; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.question_responses (id, attempt_id, question_id, selected_option_id, answer_text, is_correct, earned_score, responded_at) FROM stdin;
\.


--
-- TOC entry 5336 (class 0 OID 30005)
-- Dependencies: 244
-- Data for Name: questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.questions (id, test_version_id, topic_id, question_text, question_type, weight, sort_order) FROM stdin;
\.


--
-- TOC entry 5310 (class 0 OID 29726)
-- Dependencies: 218
-- Data for Name: roles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.roles (id, code) FROM stdin;
1	employer
2	manager
3	admin
\.


--
-- TOC entry 5346 (class 0 OID 30123)
-- Dependencies: 254
-- Data for Name: scenario_steps; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.scenario_steps (id, scenario_id, step_code, step_name, stage_type, expected_result, sort_order) FROM stdin;
\.


--
-- TOC entry 5348 (class 0 OID 30143)
-- Dependencies: 256
-- Data for Name: scenario_transitions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.scenario_transitions (id, scenario_id, from_step_id, to_step_id, transition_condition, transition_type) FROM stdin;
\.


--
-- TOC entry 5344 (class 0 OID 30098)
-- Dependencies: 252
-- Data for Name: scenarios; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.scenarios (id, company_id, title, scenario_type, description, difficulty, status, created_by, created_at) FROM stdin;
\.


--
-- TOC entry 5356 (class 0 OID 30238)
-- Dependencies: 264
-- Data for Name: session_results; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.session_results (id, session_id, total_score, strong_sides, weak_sides, missed_steps, recommendations, created_at) FROM stdin;
\.


--
-- TOC entry 5354 (class 0 OID 30213)
-- Dependencies: 262
-- Data for Name: step_evaluations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.step_evaluations (id, session_id, step_id, score, comment, funnel_stage_score, product_score, objection_score, script_score, created_at) FROM stdin;
\.


--
-- TOC entry 5314 (class 0 OID 29746)
-- Dependencies: 222
-- Data for Name: teams; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teams (id, company_id, name, created_at, manager_user_id) FROM stdin;
\.


--
-- TOC entry 5340 (class 0 OID 30043)
-- Dependencies: 248
-- Data for Name: test_attempts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.test_attempts (id, user_id, test_id, test_version_id, attempt_no, started_at, completed_at, score, percent, status) FROM stdin;
\.


--
-- TOC entry 5334 (class 0 OID 29978)
-- Dependencies: 242
-- Data for Name: test_versions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.test_versions (id, test_id, version_number, created_by, approved_by, approved_at, status, created_at) FROM stdin;
\.


--
-- TOC entry 5332 (class 0 OID 29944)
-- Dependencies: 240
-- Data for Name: tests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tests (id, company_id, course_id, topic_id, title, test_type, status, current_version_no, created_by, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5370 (class 0 OID 30387)
-- Dependencies: 278
-- Data for Name: topic_error_mart; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.topic_error_mart (id, company_id, topic_id, period_start, period_end, error_count, avg_score) FROM stdin;
\.


--
-- TOC entry 5350 (class 0 OID 30169)
-- Dependencies: 258
-- Data for Name: training_sessions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.training_sessions (id, user_id, scenario_id, started_at, completed_at, mode, status, final_score) FROM stdin;
\.


--
-- TOC entry 5316 (class 0 OID 29761)
-- Dependencies: 224
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, company_id, team_id, role_id, full_name, email, password_hash, is_active, created_at) FROM stdin;
\.


--
-- TOC entry 5410 (class 0 OID 0)
-- Dependencies: 271
-- Name: activity_events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.activity_events_id_seq', 1, false);


--
-- TOC entry 5411 (class 0 OID 0)
-- Dependencies: 267
-- Name: bot_queries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bot_queries_id_seq', 1, false);


--
-- TOC entry 5412 (class 0 OID 0)
-- Dependencies: 269
-- Name: bot_query_sources_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.bot_query_sources_id_seq', 1, false);


--
-- TOC entry 5413 (class 0 OID 0)
-- Dependencies: 265
-- Name: chat_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.chat_sessions_id_seq', 1, false);


--
-- TOC entry 5414 (class 0 OID 0)
-- Dependencies: 219
-- Name: companies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.companies_id_seq', 1, false);


--
-- TOC entry 5415 (class 0 OID 0)
-- Dependencies: 237
-- Name: course_document_links_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_document_links_id_seq', 1, false);


--
-- TOC entry 5416 (class 0 OID 0)
-- Dependencies: 233
-- Name: course_modules_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_modules_id_seq', 1, false);


--
-- TOC entry 5417 (class 0 OID 0)
-- Dependencies: 235
-- Name: course_topics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_topics_id_seq', 1, false);


--
-- TOC entry 5418 (class 0 OID 0)
-- Dependencies: 231
-- Name: course_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.course_versions_id_seq', 1, false);


--
-- TOC entry 5419 (class 0 OID 0)
-- Dependencies: 229
-- Name: courses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.courses_id_seq', 1, false);


--
-- TOC entry 5420 (class 0 OID 0)
-- Dependencies: 259
-- Name: dialog_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.dialog_messages_id_seq', 1, false);


--
-- TOC entry 5421 (class 0 OID 0)
-- Dependencies: 279
-- Name: dialog_stage_mart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.dialog_stage_mart_id_seq', 1, false);


--
-- TOC entry 5422 (class 0 OID 0)
-- Dependencies: 227
-- Name: document_chunks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.document_chunks_id_seq', 1, false);


--
-- TOC entry 5423 (class 0 OID 0)
-- Dependencies: 225
-- Name: documents_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.documents_id_seq', 1, false);


--
-- TOC entry 5424 (class 0 OID 0)
-- Dependencies: 273
-- Name: employee_progress_mart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.employee_progress_mart_id_seq', 1, false);


--
-- TOC entry 5425 (class 0 OID 0)
-- Dependencies: 275
-- Name: group_progress_mart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.group_progress_mart_id_seq', 1, false);


--
-- TOC entry 5426 (class 0 OID 0)
-- Dependencies: 245
-- Name: question_options_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.question_options_id_seq', 1, false);


--
-- TOC entry 5427 (class 0 OID 0)
-- Dependencies: 249
-- Name: question_responses_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.question_responses_id_seq', 1, false);


--
-- TOC entry 5428 (class 0 OID 0)
-- Dependencies: 243
-- Name: questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.questions_id_seq', 1, false);


--
-- TOC entry 5429 (class 0 OID 0)
-- Dependencies: 217
-- Name: roles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.roles_id_seq', 3, true);


--
-- TOC entry 5430 (class 0 OID 0)
-- Dependencies: 253
-- Name: scenario_steps_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.scenario_steps_id_seq', 1, false);


--
-- TOC entry 5431 (class 0 OID 0)
-- Dependencies: 255
-- Name: scenario_transitions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.scenario_transitions_id_seq', 1, false);


--
-- TOC entry 5432 (class 0 OID 0)
-- Dependencies: 251
-- Name: scenarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.scenarios_id_seq', 1, false);


--
-- TOC entry 5433 (class 0 OID 0)
-- Dependencies: 263
-- Name: session_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.session_results_id_seq', 1, false);


--
-- TOC entry 5434 (class 0 OID 0)
-- Dependencies: 261
-- Name: step_evaluations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.step_evaluations_id_seq', 1, false);


--
-- TOC entry 5435 (class 0 OID 0)
-- Dependencies: 221
-- Name: teams_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.teams_id_seq', 1, false);


--
-- TOC entry 5436 (class 0 OID 0)
-- Dependencies: 247
-- Name: test_attempts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.test_attempts_id_seq', 1, false);


--
-- TOC entry 5437 (class 0 OID 0)
-- Dependencies: 241
-- Name: test_versions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.test_versions_id_seq', 1, false);


--
-- TOC entry 5438 (class 0 OID 0)
-- Dependencies: 239
-- Name: tests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.tests_id_seq', 1, false);


--
-- TOC entry 5439 (class 0 OID 0)
-- Dependencies: 277
-- Name: topic_error_mart_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.topic_error_mart_id_seq', 1, false);


--
-- TOC entry 5440 (class 0 OID 0)
-- Dependencies: 257
-- Name: training_sessions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.training_sessions_id_seq', 1, false);


--
-- TOC entry 5441 (class 0 OID 0)
-- Dependencies: 223
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 1, false);


--
-- TOC entry 5075 (class 2606 OID 30329)
-- Name: activity_events activity_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_events
    ADD CONSTRAINT activity_events_pkey PRIMARY KEY (id);


--
-- TOC entry 5068 (class 2606 OID 30277)
-- Name: bot_queries bot_queries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_queries
    ADD CONSTRAINT bot_queries_pkey PRIMARY KEY (id);


--
-- TOC entry 5072 (class 2606 OID 30304)
-- Name: bot_query_sources bot_query_sources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_query_sources
    ADD CONSTRAINT bot_query_sources_pkey PRIMARY KEY (id);


--
-- TOC entry 5065 (class 2606 OID 30262)
-- Name: chat_sessions chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_pkey PRIMARY KEY (id);


--
-- TOC entry 4973 (class 2606 OID 29744)
-- Name: companies companies_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_name_key UNIQUE (name);


--
-- TOC entry 4975 (class 2606 OID 29742)
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- TOC entry 5011 (class 2606 OID 29932)
-- Name: course_document_links course_document_links_course_id_document_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_document_links
    ADD CONSTRAINT course_document_links_course_id_document_id_key UNIQUE (course_id, document_id);


--
-- TOC entry 5013 (class 2606 OID 29930)
-- Name: course_document_links course_document_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_document_links
    ADD CONSTRAINT course_document_links_pkey PRIMARY KEY (id);


--
-- TOC entry 5005 (class 2606 OID 29898)
-- Name: course_modules course_modules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_modules
    ADD CONSTRAINT course_modules_pkey PRIMARY KEY (id);


--
-- TOC entry 5008 (class 2606 OID 29913)
-- Name: course_topics course_topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_topics
    ADD CONSTRAINT course_topics_pkey PRIMARY KEY (id);


--
-- TOC entry 5000 (class 2606 OID 29870)
-- Name: course_versions course_versions_course_id_version_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_course_id_version_number_key UNIQUE (course_id, version_number);


--
-- TOC entry 5002 (class 2606 OID 29868)
-- Name: course_versions course_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_pkey PRIMARY KEY (id);


--
-- TOC entry 4997 (class 2606 OID 29846)
-- Name: courses courses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_pkey PRIMARY KEY (id);


--
-- TOC entry 5055 (class 2606 OID 30201)
-- Name: dialog_messages dialog_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_messages
    ADD CONSTRAINT dialog_messages_pkey PRIMARY KEY (id);


--
-- TOC entry 5093 (class 2606 OID 30418)
-- Name: dialog_stage_mart dialog_stage_mart_company_id_user_id_scenario_id_stage_type_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_stage_mart
    ADD CONSTRAINT dialog_stage_mart_company_id_user_id_scenario_id_stage_type_key UNIQUE (company_id, user_id, scenario_id, stage_type, period_start, period_end);


--
-- TOC entry 5095 (class 2606 OID 30416)
-- Name: dialog_stage_mart dialog_stage_mart_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_stage_mart
    ADD CONSTRAINT dialog_stage_mart_pkey PRIMARY KEY (id);


--
-- TOC entry 4992 (class 2606 OID 29827)
-- Name: document_chunks document_chunks_document_id_chunk_index_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_id_chunk_index_key UNIQUE (document_id, chunk_index);


--
-- TOC entry 4994 (class 2606 OID 29825)
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


--
-- TOC entry 4988 (class 2606 OID 29805)
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- TOC entry 5080 (class 2606 OID 30353)
-- Name: employee_progress_mart employee_progress_mart_company_id_user_id_period_start_peri_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_progress_mart
    ADD CONSTRAINT employee_progress_mart_company_id_user_id_period_start_peri_key UNIQUE (company_id, user_id, period_start, period_end);


--
-- TOC entry 5082 (class 2606 OID 30351)
-- Name: employee_progress_mart employee_progress_mart_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_progress_mart
    ADD CONSTRAINT employee_progress_mart_pkey PRIMARY KEY (id);


--
-- TOC entry 5085 (class 2606 OID 30375)
-- Name: group_progress_mart group_progress_mart_company_id_team_id_period_start_period__key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_progress_mart
    ADD CONSTRAINT group_progress_mart_company_id_team_id_period_start_period__key UNIQUE (company_id, team_id, period_start, period_end);


--
-- TOC entry 5087 (class 2606 OID 30373)
-- Name: group_progress_mart group_progress_mart_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_progress_mart
    ADD CONSTRAINT group_progress_mart_pkey PRIMARY KEY (id);


--
-- TOC entry 5028 (class 2606 OID 30036)
-- Name: question_options question_options_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_options
    ADD CONSTRAINT question_options_pkey PRIMARY KEY (id);


--
-- TOC entry 5037 (class 2606 OID 30081)
-- Name: question_responses question_responses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_responses
    ADD CONSTRAINT question_responses_pkey PRIMARY KEY (id);


--
-- TOC entry 5025 (class 2606 OID 30015)
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- TOC entry 4969 (class 2606 OID 29734)
-- Name: roles roles_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_code_key UNIQUE (code);


--
-- TOC entry 4971 (class 2606 OID 29732)
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id);


--
-- TOC entry 5043 (class 2606 OID 30132)
-- Name: scenario_steps scenario_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_steps
    ADD CONSTRAINT scenario_steps_pkey PRIMARY KEY (id);


--
-- TOC entry 5045 (class 2606 OID 30136)
-- Name: scenario_steps scenario_steps_scenario_id_sort_order_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_steps
    ADD CONSTRAINT scenario_steps_scenario_id_sort_order_key UNIQUE (scenario_id, sort_order);


--
-- TOC entry 5047 (class 2606 OID 30134)
-- Name: scenario_steps scenario_steps_scenario_id_step_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_steps
    ADD CONSTRAINT scenario_steps_scenario_id_step_code_key UNIQUE (scenario_id, step_code);


--
-- TOC entry 5049 (class 2606 OID 30152)
-- Name: scenario_transitions scenario_transitions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_transitions
    ADD CONSTRAINT scenario_transitions_pkey PRIMARY KEY (id);


--
-- TOC entry 5040 (class 2606 OID 30111)
-- Name: scenarios scenarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_pkey PRIMARY KEY (id);


--
-- TOC entry 5061 (class 2606 OID 30247)
-- Name: session_results session_results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_results
    ADD CONSTRAINT session_results_pkey PRIMARY KEY (id);


--
-- TOC entry 5063 (class 2606 OID 30249)
-- Name: session_results session_results_session_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_results
    ADD CONSTRAINT session_results_session_id_key UNIQUE (session_id);


--
-- TOC entry 5059 (class 2606 OID 30226)
-- Name: step_evaluations step_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.step_evaluations
    ADD CONSTRAINT step_evaluations_pkey PRIMARY KEY (id);


--
-- TOC entry 4977 (class 2606 OID 29754)
-- Name: teams teams_company_id_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_company_id_name_key UNIQUE (company_id, name);


--
-- TOC entry 4979 (class 2606 OID 29752)
-- Name: teams teams_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_pkey PRIMARY KEY (id);


--
-- TOC entry 5032 (class 2606 OID 30053)
-- Name: test_attempts test_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_attempts
    ADD CONSTRAINT test_attempts_pkey PRIMARY KEY (id);


--
-- TOC entry 5034 (class 2606 OID 30055)
-- Name: test_attempts test_attempts_user_id_test_id_attempt_no_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_attempts
    ADD CONSTRAINT test_attempts_user_id_test_id_attempt_no_key UNIQUE (user_id, test_id, attempt_no);


--
-- TOC entry 5020 (class 2606 OID 29986)
-- Name: test_versions test_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_versions
    ADD CONSTRAINT test_versions_pkey PRIMARY KEY (id);


--
-- TOC entry 5022 (class 2606 OID 29988)
-- Name: test_versions test_versions_test_id_version_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_versions
    ADD CONSTRAINT test_versions_test_id_version_number_key UNIQUE (test_id, version_number);


--
-- TOC entry 5017 (class 2606 OID 29956)
-- Name: tests tests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_pkey PRIMARY KEY (id);


--
-- TOC entry 5091 (class 2606 OID 30394)
-- Name: topic_error_mart topic_error_mart_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic_error_mart
    ADD CONSTRAINT topic_error_mart_pkey PRIMARY KEY (id);


--
-- TOC entry 5053 (class 2606 OID 30180)
-- Name: training_sessions training_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT training_sessions_pkey PRIMARY KEY (id);


--
-- TOC entry 4984 (class 2606 OID 29772)
-- Name: users users_company_id_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_company_id_email_key UNIQUE (company_id, email);


--
-- TOC entry 4986 (class 2606 OID 29770)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 5076 (class 1259 OID 30462)
-- Name: idx_activity_events_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_activity_events_company_id ON public.activity_events USING btree (company_id);


--
-- TOC entry 5077 (class 1259 OID 30464)
-- Name: idx_activity_events_event_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_activity_events_event_time ON public.activity_events USING btree (event_time);


--
-- TOC entry 5078 (class 1259 OID 30463)
-- Name: idx_activity_events_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_activity_events_user_id ON public.activity_events USING btree (user_id);


--
-- TOC entry 5069 (class 1259 OID 30460)
-- Name: idx_bot_queries_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_bot_queries_company_id ON public.bot_queries USING btree (company_id);


--
-- TOC entry 5070 (class 1259 OID 30459)
-- Name: idx_bot_queries_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_bot_queries_user_id ON public.bot_queries USING btree (user_id);


--
-- TOC entry 5073 (class 1259 OID 30461)
-- Name: idx_bot_query_sources_bot_query_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_bot_query_sources_bot_query_id ON public.bot_query_sources USING btree (bot_query_id);


--
-- TOC entry 5066 (class 1259 OID 30458)
-- Name: idx_chat_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_chat_sessions_user_id ON public.chat_sessions USING btree (user_id);


--
-- TOC entry 5006 (class 1259 OID 30442)
-- Name: idx_course_modules_course_version_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_course_modules_course_version_id ON public.course_modules USING btree (course_version_id);


--
-- TOC entry 5009 (class 1259 OID 30443)
-- Name: idx_course_topics_module_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_course_topics_module_id ON public.course_topics USING btree (module_id);


--
-- TOC entry 5003 (class 1259 OID 30441)
-- Name: idx_course_versions_course_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_course_versions_course_id ON public.course_versions USING btree (course_id);


--
-- TOC entry 4998 (class 1259 OID 30440)
-- Name: idx_courses_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_courses_company_id ON public.courses USING btree (company_id);


--
-- TOC entry 5056 (class 1259 OID 30456)
-- Name: idx_dialog_messages_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dialog_messages_session_id ON public.dialog_messages USING btree (session_id);


--
-- TOC entry 5096 (class 1259 OID 30468)
-- Name: idx_dialog_stage_mart_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_dialog_stage_mart_user_id ON public.dialog_stage_mart USING btree (user_id);


--
-- TOC entry 4995 (class 1259 OID 30439)
-- Name: idx_document_chunks_document_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_document_chunks_document_id ON public.document_chunks USING btree (document_id);


--
-- TOC entry 4989 (class 1259 OID 30437)
-- Name: idx_documents_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_company_id ON public.documents USING btree (company_id);


--
-- TOC entry 4990 (class 1259 OID 30438)
-- Name: idx_documents_uploaded_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_documents_uploaded_by ON public.documents USING btree (uploaded_by);


--
-- TOC entry 5083 (class 1259 OID 30465)
-- Name: idx_employee_progress_mart_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_employee_progress_mart_user_id ON public.employee_progress_mart USING btree (user_id);


--
-- TOC entry 5088 (class 1259 OID 30466)
-- Name: idx_group_progress_mart_team_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_group_progress_mart_team_id ON public.group_progress_mart USING btree (team_id);


--
-- TOC entry 5026 (class 1259 OID 30448)
-- Name: idx_question_options_question_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_question_options_question_id ON public.question_options USING btree (question_id);


--
-- TOC entry 5035 (class 1259 OID 30451)
-- Name: idx_question_responses_attempt_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_question_responses_attempt_id ON public.question_responses USING btree (attempt_id);


--
-- TOC entry 5023 (class 1259 OID 30447)
-- Name: idx_questions_test_version_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_questions_test_version_id ON public.questions USING btree (test_version_id);


--
-- TOC entry 5041 (class 1259 OID 30453)
-- Name: idx_scenario_steps_scenario_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_scenario_steps_scenario_id ON public.scenario_steps USING btree (scenario_id);


--
-- TOC entry 5038 (class 1259 OID 30452)
-- Name: idx_scenarios_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_scenarios_company_id ON public.scenarios USING btree (company_id);


--
-- TOC entry 5057 (class 1259 OID 30457)
-- Name: idx_step_evaluations_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_step_evaluations_session_id ON public.step_evaluations USING btree (session_id);


--
-- TOC entry 5029 (class 1259 OID 30450)
-- Name: idx_test_attempts_test_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_test_attempts_test_id ON public.test_attempts USING btree (test_id);


--
-- TOC entry 5030 (class 1259 OID 30449)
-- Name: idx_test_attempts_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_test_attempts_user_id ON public.test_attempts USING btree (user_id);


--
-- TOC entry 5018 (class 1259 OID 30446)
-- Name: idx_test_versions_test_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_test_versions_test_id ON public.test_versions USING btree (test_id);


--
-- TOC entry 5014 (class 1259 OID 30444)
-- Name: idx_tests_course_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tests_course_id ON public.tests USING btree (course_id);


--
-- TOC entry 5015 (class 1259 OID 30445)
-- Name: idx_tests_topic_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_tests_topic_id ON public.tests USING btree (topic_id);


--
-- TOC entry 5089 (class 1259 OID 30467)
-- Name: idx_topic_error_mart_topic_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_topic_error_mart_topic_id ON public.topic_error_mart USING btree (topic_id);


--
-- TOC entry 5050 (class 1259 OID 30455)
-- Name: idx_training_sessions_scenario_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_training_sessions_scenario_id ON public.training_sessions USING btree (scenario_id);


--
-- TOC entry 5051 (class 1259 OID 30454)
-- Name: idx_training_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_training_sessions_user_id ON public.training_sessions USING btree (user_id);


--
-- TOC entry 4980 (class 1259 OID 30434)
-- Name: idx_users_company_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_company_id ON public.users USING btree (company_id);


--
-- TOC entry 4981 (class 1259 OID 30436)
-- Name: idx_users_role_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_role_id ON public.users USING btree (role_id);


--
-- TOC entry 4982 (class 1259 OID 30435)
-- Name: idx_users_team_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_team_id ON public.users USING btree (team_id);


--
-- TOC entry 5153 (class 2606 OID 30330)
-- Name: activity_events activity_events_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_events
    ADD CONSTRAINT activity_events_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5154 (class 2606 OID 30335)
-- Name: activity_events activity_events_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_events
    ADD CONSTRAINT activity_events_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5146 (class 2606 OID 30278)
-- Name: bot_queries bot_queries_chat_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_queries
    ADD CONSTRAINT bot_queries_chat_session_id_fkey FOREIGN KEY (chat_session_id) REFERENCES public.chat_sessions(id) ON DELETE SET NULL;


--
-- TOC entry 5147 (class 2606 OID 30288)
-- Name: bot_queries bot_queries_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_queries
    ADD CONSTRAINT bot_queries_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5148 (class 2606 OID 30293)
-- Name: bot_queries bot_queries_training_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_queries
    ADD CONSTRAINT bot_queries_training_session_id_fkey FOREIGN KEY (training_session_id) REFERENCES public.training_sessions(id) ON DELETE SET NULL;


--
-- TOC entry 5149 (class 2606 OID 30283)
-- Name: bot_queries bot_queries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_queries
    ADD CONSTRAINT bot_queries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5150 (class 2606 OID 30305)
-- Name: bot_query_sources bot_query_sources_bot_query_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_query_sources
    ADD CONSTRAINT bot_query_sources_bot_query_id_fkey FOREIGN KEY (bot_query_id) REFERENCES public.bot_queries(id) ON DELETE CASCADE;


--
-- TOC entry 5151 (class 2606 OID 30315)
-- Name: bot_query_sources bot_query_sources_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_query_sources
    ADD CONSTRAINT bot_query_sources_chunk_id_fkey FOREIGN KEY (chunk_id) REFERENCES public.document_chunks(id) ON DELETE SET NULL;


--
-- TOC entry 5152 (class 2606 OID 30310)
-- Name: bot_query_sources bot_query_sources_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bot_query_sources
    ADD CONSTRAINT bot_query_sources_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 5145 (class 2606 OID 30263)
-- Name: chat_sessions chat_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_sessions
    ADD CONSTRAINT chat_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5114 (class 2606 OID 29933)
-- Name: course_document_links course_document_links_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_document_links
    ADD CONSTRAINT course_document_links_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- TOC entry 5115 (class 2606 OID 29938)
-- Name: course_document_links course_document_links_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_document_links
    ADD CONSTRAINT course_document_links_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 5111 (class 2606 OID 29899)
-- Name: course_modules course_modules_course_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_modules
    ADD CONSTRAINT course_modules_course_version_id_fkey FOREIGN KEY (course_version_id) REFERENCES public.course_versions(id) ON DELETE CASCADE;


--
-- TOC entry 5112 (class 2606 OID 29914)
-- Name: course_topics course_topics_module_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_topics
    ADD CONSTRAINT course_topics_module_id_fkey FOREIGN KEY (module_id) REFERENCES public.course_modules(id) ON DELETE CASCADE;


--
-- TOC entry 5113 (class 2606 OID 29919)
-- Name: course_topics course_topics_source_chunk_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_topics
    ADD CONSTRAINT course_topics_source_chunk_id_fkey FOREIGN KEY (source_chunk_id) REFERENCES public.document_chunks(id) ON DELETE SET NULL;


--
-- TOC entry 5107 (class 2606 OID 29886)
-- Name: course_versions course_versions_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5108 (class 2606 OID 29871)
-- Name: course_versions course_versions_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- TOC entry 5109 (class 2606 OID 29881)
-- Name: course_versions course_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5110 (class 2606 OID 29876)
-- Name: course_versions course_versions_generated_from_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.course_versions
    ADD CONSTRAINT course_versions_generated_from_document_id_fkey FOREIGN KEY (generated_from_document_id) REFERENCES public.documents(id) ON DELETE SET NULL;


--
-- TOC entry 5105 (class 2606 OID 29847)
-- Name: courses courses_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5106 (class 2606 OID 29852)
-- Name: courses courses_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT courses_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5140 (class 2606 OID 30202)
-- Name: dialog_messages dialog_messages_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_messages
    ADD CONSTRAINT dialog_messages_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.training_sessions(id) ON DELETE CASCADE;


--
-- TOC entry 5141 (class 2606 OID 30207)
-- Name: dialog_messages dialog_messages_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_messages
    ADD CONSTRAINT dialog_messages_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.scenario_steps(id) ON DELETE SET NULL;


--
-- TOC entry 5161 (class 2606 OID 30419)
-- Name: dialog_stage_mart dialog_stage_mart_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_stage_mart
    ADD CONSTRAINT dialog_stage_mart_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5162 (class 2606 OID 30429)
-- Name: dialog_stage_mart dialog_stage_mart_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_stage_mart
    ADD CONSTRAINT dialog_stage_mart_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE CASCADE;


--
-- TOC entry 5163 (class 2606 OID 30424)
-- Name: dialog_stage_mart dialog_stage_mart_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dialog_stage_mart
    ADD CONSTRAINT dialog_stage_mart_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5104 (class 2606 OID 29828)
-- Name: document_chunks document_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(id) ON DELETE CASCADE;


--
-- TOC entry 5102 (class 2606 OID 29806)
-- Name: documents documents_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5103 (class 2606 OID 29811)
-- Name: documents documents_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5155 (class 2606 OID 30354)
-- Name: employee_progress_mart employee_progress_mart_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_progress_mart
    ADD CONSTRAINT employee_progress_mart_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5156 (class 2606 OID 30359)
-- Name: employee_progress_mart employee_progress_mart_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_progress_mart
    ADD CONSTRAINT employee_progress_mart_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5157 (class 2606 OID 30376)
-- Name: group_progress_mart group_progress_mart_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_progress_mart
    ADD CONSTRAINT group_progress_mart_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5158 (class 2606 OID 30381)
-- Name: group_progress_mart group_progress_mart_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.group_progress_mart
    ADD CONSTRAINT group_progress_mart_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE SET NULL;


--
-- TOC entry 5125 (class 2606 OID 30037)
-- Name: question_options question_options_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_options
    ADD CONSTRAINT question_options_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE;


--
-- TOC entry 5129 (class 2606 OID 30082)
-- Name: question_responses question_responses_attempt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_responses
    ADD CONSTRAINT question_responses_attempt_id_fkey FOREIGN KEY (attempt_id) REFERENCES public.test_attempts(id) ON DELETE CASCADE;


--
-- TOC entry 5130 (class 2606 OID 30087)
-- Name: question_responses question_responses_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_responses
    ADD CONSTRAINT question_responses_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE;


--
-- TOC entry 5131 (class 2606 OID 30092)
-- Name: question_responses question_responses_selected_option_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.question_responses
    ADD CONSTRAINT question_responses_selected_option_id_fkey FOREIGN KEY (selected_option_id) REFERENCES public.question_options(id) ON DELETE SET NULL;


--
-- TOC entry 5123 (class 2606 OID 30016)
-- Name: questions questions_test_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_test_version_id_fkey FOREIGN KEY (test_version_id) REFERENCES public.test_versions(id) ON DELETE CASCADE;


--
-- TOC entry 5124 (class 2606 OID 30021)
-- Name: questions questions_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.course_topics(id) ON DELETE SET NULL;


--
-- TOC entry 5134 (class 2606 OID 30137)
-- Name: scenario_steps scenario_steps_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_steps
    ADD CONSTRAINT scenario_steps_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE CASCADE;


--
-- TOC entry 5135 (class 2606 OID 30158)
-- Name: scenario_transitions scenario_transitions_from_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_transitions
    ADD CONSTRAINT scenario_transitions_from_step_id_fkey FOREIGN KEY (from_step_id) REFERENCES public.scenario_steps(id) ON DELETE CASCADE;


--
-- TOC entry 5136 (class 2606 OID 30153)
-- Name: scenario_transitions scenario_transitions_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_transitions
    ADD CONSTRAINT scenario_transitions_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE CASCADE;


--
-- TOC entry 5137 (class 2606 OID 30163)
-- Name: scenario_transitions scenario_transitions_to_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_transitions
    ADD CONSTRAINT scenario_transitions_to_step_id_fkey FOREIGN KEY (to_step_id) REFERENCES public.scenario_steps(id) ON DELETE CASCADE;


--
-- TOC entry 5132 (class 2606 OID 30112)
-- Name: scenarios scenarios_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5133 (class 2606 OID 30117)
-- Name: scenarios scenarios_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5144 (class 2606 OID 30250)
-- Name: session_results session_results_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.session_results
    ADD CONSTRAINT session_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.training_sessions(id) ON DELETE CASCADE;


--
-- TOC entry 5142 (class 2606 OID 30227)
-- Name: step_evaluations step_evaluations_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.step_evaluations
    ADD CONSTRAINT step_evaluations_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.training_sessions(id) ON DELETE CASCADE;


--
-- TOC entry 5143 (class 2606 OID 30232)
-- Name: step_evaluations step_evaluations_step_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.step_evaluations
    ADD CONSTRAINT step_evaluations_step_id_fkey FOREIGN KEY (step_id) REFERENCES public.scenario_steps(id) ON DELETE CASCADE;


--
-- TOC entry 5097 (class 2606 OID 29755)
-- Name: teams teams_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5098 (class 2606 OID 29788)
-- Name: teams teams_manager_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teams
    ADD CONSTRAINT teams_manager_user_id_fkey FOREIGN KEY (manager_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5126 (class 2606 OID 30061)
-- Name: test_attempts test_attempts_test_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_attempts
    ADD CONSTRAINT test_attempts_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.tests(id) ON DELETE CASCADE;


--
-- TOC entry 5127 (class 2606 OID 30066)
-- Name: test_attempts test_attempts_test_version_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_attempts
    ADD CONSTRAINT test_attempts_test_version_id_fkey FOREIGN KEY (test_version_id) REFERENCES public.test_versions(id) ON DELETE CASCADE;


--
-- TOC entry 5128 (class 2606 OID 30056)
-- Name: test_attempts test_attempts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_attempts
    ADD CONSTRAINT test_attempts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5120 (class 2606 OID 29999)
-- Name: test_versions test_versions_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_versions
    ADD CONSTRAINT test_versions_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5121 (class 2606 OID 29994)
-- Name: test_versions test_versions_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_versions
    ADD CONSTRAINT test_versions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5122 (class 2606 OID 29989)
-- Name: test_versions test_versions_test_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.test_versions
    ADD CONSTRAINT test_versions_test_id_fkey FOREIGN KEY (test_id) REFERENCES public.tests(id) ON DELETE CASCADE;


--
-- TOC entry 5116 (class 2606 OID 29957)
-- Name: tests tests_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5117 (class 2606 OID 29962)
-- Name: tests tests_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE CASCADE;


--
-- TOC entry 5118 (class 2606 OID 29972)
-- Name: tests tests_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- TOC entry 5119 (class 2606 OID 29967)
-- Name: tests tests_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tests
    ADD CONSTRAINT tests_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.course_topics(id) ON DELETE SET NULL;


--
-- TOC entry 5159 (class 2606 OID 30395)
-- Name: topic_error_mart topic_error_mart_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic_error_mart
    ADD CONSTRAINT topic_error_mart_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5160 (class 2606 OID 30400)
-- Name: topic_error_mart topic_error_mart_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topic_error_mart
    ADD CONSTRAINT topic_error_mart_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.course_topics(id) ON DELETE CASCADE;


--
-- TOC entry 5138 (class 2606 OID 30186)
-- Name: training_sessions training_sessions_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT training_sessions_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE CASCADE;


--
-- TOC entry 5139 (class 2606 OID 30181)
-- Name: training_sessions training_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.training_sessions
    ADD CONSTRAINT training_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5099 (class 2606 OID 29773)
-- Name: users users_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 5100 (class 2606 OID 29783)
-- Name: users users_role_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_role_id_fkey FOREIGN KEY (role_id) REFERENCES public.roles(id);


--
-- TOC entry 5101 (class 2606 OID 29778)
-- Name: users users_team_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_team_id_fkey FOREIGN KEY (team_id) REFERENCES public.teams(id) ON DELETE SET NULL;


-- Completed on 2026-04-05 21:52:45

--
-- PostgreSQL database dump complete
--

\unrestrict l0LgGfq1QG1QAxzeZkUmGInaiduugR99hHabsPC4o8KyajAGy2aLL6L99egdOQh

