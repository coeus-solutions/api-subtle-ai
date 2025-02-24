--
-- PostgreSQL database dump
--

-- Dumped from database version 15.8
-- Dumped by pg_dump version 17.2 (Ubuntu 17.2-1.pgdg22.04+1)

-- Started on 2025-02-24 16:28:11 PKT

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

--
-- TOC entry 20 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- TOC entry 3861 (class 0 OID 0)
-- Dependencies: 20
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- TOC entry 460 (class 1255 OID 29531)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 276 (class 1259 OID 29664)
-- Name: subtitles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subtitles (
    id integer NOT NULL,
    uuid uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    video_id integer,
    subtitle_url text NOT NULL,
    format character varying(10) DEFAULT 'srt'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    language character varying(5) DEFAULT 'en'::character varying
);


ALTER TABLE public.subtitles OWNER TO postgres;

--
-- TOC entry 3864 (class 0 OID 0)
-- Dependencies: 276
-- Name: TABLE subtitles; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.subtitles IS 'Stores generated subtitle files';


--
-- TOC entry 3865 (class 0 OID 0)
-- Dependencies: 276
-- Name: COLUMN subtitles.format; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.subtitles.format IS 'Format of subtitle file: srt or vtt';


--
-- TOC entry 277 (class 1259 OID 29673)
-- Name: subtitles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subtitles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.subtitles_id_seq OWNER TO postgres;

--
-- TOC entry 3867 (class 0 OID 0)
-- Dependencies: 277
-- Name: subtitles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subtitles_id_seq OWNED BY public.subtitles.id;


--
-- TOC entry 278 (class 1259 OID 29674)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    uuid uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    email character varying(255) NOT NULL,
    password_hash character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    minutes_consumed numeric(10,2) DEFAULT 0,
    free_minutes_used numeric(10,2) DEFAULT 0,
    total_cost numeric(10,2) DEFAULT 0,
    allowed_minutes double precision DEFAULT 30.0 NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 3869 (class 0 OID 0)
-- Dependencies: 278
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.users IS 'Stores user account information';


--
-- TOC entry 279 (class 1259 OID 29682)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 3871 (class 0 OID 0)
-- Dependencies: 279
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- TOC entry 280 (class 1259 OID 29683)
-- Name: videos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.videos (
    id integer NOT NULL,
    uuid uuid DEFAULT extensions.uuid_generate_v4() NOT NULL,
    user_id integer,
    video_url text NOT NULL,
    status character varying(50) DEFAULT 'queued'::character varying,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    original_name character varying(255),
    duration_minutes numeric(10,2) DEFAULT 0,
    dubbed_video_url character varying,
    dubbing_id character varying,
    is_dubbed_audio boolean DEFAULT false,
    language character varying(10) DEFAULT 'en'::character varying,
    burned_video_url text,
    subtitle_styles jsonb
);


ALTER TABLE public.videos OWNER TO postgres;

--
-- TOC entry 3873 (class 0 OID 0)
-- Dependencies: 280
-- Name: TABLE videos; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.videos IS 'Stores uploaded video information';


--
-- TOC entry 3874 (class 0 OID 0)
-- Dependencies: 280
-- Name: COLUMN videos.status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.videos.status IS 'Status of video processing: queued, processing, completed, or failed';


--
-- TOC entry 281 (class 1259 OID 29692)
-- Name: videos_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.videos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.videos_id_seq OWNER TO postgres;

--
-- TOC entry 3876 (class 0 OID 0)
-- Dependencies: 281
-- Name: videos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.videos_id_seq OWNED BY public.videos.id;


--
-- TOC entry 3658 (class 2604 OID 29752)
-- Name: subtitles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subtitles ALTER COLUMN id SET DEFAULT nextval('public.subtitles_id_seq'::regclass);


--
-- TOC entry 3664 (class 2604 OID 29753)
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- TOC entry 3672 (class 2604 OID 29754)
-- Name: videos id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos ALTER COLUMN id SET DEFAULT nextval('public.videos_id_seq'::regclass);


--
-- TOC entry 3683 (class 2606 OID 29804)
-- Name: subtitles subtitles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subtitles
    ADD CONSTRAINT subtitles_pkey PRIMARY KEY (id);


--
-- TOC entry 3685 (class 2606 OID 29806)
-- Name: subtitles subtitles_uuid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subtitles
    ADD CONSTRAINT subtitles_uuid_key UNIQUE (uuid);


--
-- TOC entry 3689 (class 2606 OID 29808)
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- TOC entry 3691 (class 2606 OID 29810)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 3693 (class 2606 OID 29812)
-- Name: users users_uuid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_uuid_key UNIQUE (uuid);


--
-- TOC entry 3698 (class 2606 OID 29814)
-- Name: videos videos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos
    ADD CONSTRAINT videos_pkey PRIMARY KEY (id);


--
-- TOC entry 3700 (class 2606 OID 29816)
-- Name: videos videos_uuid_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos
    ADD CONSTRAINT videos_uuid_key UNIQUE (uuid);


--
-- TOC entry 3680 (class 1259 OID 29875)
-- Name: idx_subtitles_uuid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subtitles_uuid ON public.subtitles USING btree (uuid);


--
-- TOC entry 3681 (class 1259 OID 29876)
-- Name: idx_subtitles_video_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_subtitles_video_id ON public.subtitles USING btree (video_id);


--
-- TOC entry 3686 (class 1259 OID 29877)
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- TOC entry 3687 (class 1259 OID 29878)
-- Name: idx_users_uuid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_users_uuid ON public.users USING btree (uuid);


--
-- TOC entry 3694 (class 1259 OID 29879)
-- Name: idx_videos_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_videos_status ON public.videos USING btree (status);


--
-- TOC entry 3695 (class 1259 OID 29880)
-- Name: idx_videos_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_videos_user_id ON public.videos USING btree (user_id);


--
-- TOC entry 3696 (class 1259 OID 29881)
-- Name: idx_videos_uuid; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_videos_uuid ON public.videos USING btree (uuid);


--
-- TOC entry 3703 (class 2620 OID 29889)
-- Name: subtitles update_subtitles_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_subtitles_updated_at BEFORE UPDATE ON public.subtitles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3704 (class 2620 OID 29890)
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3705 (class 2620 OID 29891)
-- Name: videos update_videos_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_videos_updated_at BEFORE UPDATE ON public.videos FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 3701 (class 2606 OID 29954)
-- Name: subtitles subtitles_video_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subtitles
    ADD CONSTRAINT subtitles_video_id_fkey FOREIGN KEY (video_id) REFERENCES public.videos(id) ON DELETE CASCADE;


--
-- TOC entry 3702 (class 2606 OID 29959)
-- Name: videos videos_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.videos
    ADD CONSTRAINT videos_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 3862 (class 0 OID 0)
-- Dependencies: 20
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT USAGE ON SCHEMA public TO postgres;
GRANT USAGE ON SCHEMA public TO anon;
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT USAGE ON SCHEMA public TO service_role;


--
-- TOC entry 3863 (class 0 OID 0)
-- Dependencies: 460
-- Name: FUNCTION update_updated_at_column(); Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON FUNCTION public.update_updated_at_column() TO anon;
GRANT ALL ON FUNCTION public.update_updated_at_column() TO authenticated;
GRANT ALL ON FUNCTION public.update_updated_at_column() TO service_role;


--
-- TOC entry 3866 (class 0 OID 0)
-- Dependencies: 276
-- Name: TABLE subtitles; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.subtitles TO anon;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.subtitles TO authenticated;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.subtitles TO service_role;


--
-- TOC entry 3868 (class 0 OID 0)
-- Dependencies: 277
-- Name: SEQUENCE subtitles_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.subtitles_id_seq TO anon;
GRANT ALL ON SEQUENCE public.subtitles_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.subtitles_id_seq TO service_role;


--
-- TOC entry 3870 (class 0 OID 0)
-- Dependencies: 278
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.users TO anon;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.users TO authenticated;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.users TO service_role;


--
-- TOC entry 3872 (class 0 OID 0)
-- Dependencies: 279
-- Name: SEQUENCE users_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.users_id_seq TO anon;
GRANT ALL ON SEQUENCE public.users_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.users_id_seq TO service_role;


--
-- TOC entry 3875 (class 0 OID 0)
-- Dependencies: 280
-- Name: TABLE videos; Type: ACL; Schema: public; Owner: postgres
--

GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.videos TO anon;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.videos TO authenticated;
GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLE public.videos TO service_role;


--
-- TOC entry 3877 (class 0 OID 0)
-- Dependencies: 281
-- Name: SEQUENCE videos_id_seq; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON SEQUENCE public.videos_id_seq TO anon;
GRANT ALL ON SEQUENCE public.videos_id_seq TO authenticated;
GRANT ALL ON SEQUENCE public.videos_id_seq TO service_role;


--
-- TOC entry 2470 (class 826 OID 30003)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- TOC entry 2473 (class 826 OID 30004)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;


--
-- TOC entry 2475 (class 826 OID 30005)
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- TOC entry 2476 (class 826 OID 30006)
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT ALL ON FUNCTIONS TO service_role;


--
-- TOC entry 2477 (class 826 OID 30007)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO service_role;


--
-- TOC entry 2479 (class 826 OID 30008)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: supabase_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin IN SCHEMA public GRANT SELECT,INSERT,REFERENCES,DELETE,TRIGGER,TRUNCATE,UPDATE ON TABLES TO service_role;


-- Completed on 2025-02-24 16:28:32 PKT

--
-- PostgreSQL database dump complete
--
