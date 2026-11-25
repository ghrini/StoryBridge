import { useCallback, useEffect, useRef, useState } from "react";
import Hero from "./components/Hero.jsx";
import HostedNotice from "./components/HostedNotice.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import NewProjectForm from "./components/NewProjectForm.jsx";
import StatusBar from "./components/StatusBar.jsx";
import SiteFooter from "./components/SiteFooter.jsx";
import StoryList from "./components/StoryList.jsx";
import ProjectPage from "./pages/ProjectPage.jsx";
import { createProject, getConfig, listProjects } from "./services/api.js";
import { HOSTED } from "./services/hosted.js";

const reduceMotion = () => window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

/** Everything on one page: the banner, how it works, your stories / start a story, and the open story. */
export default function App() {
  const [config, setConfig] = useState(null);
  const [projects, setProjects] = useState(null);
  const [projectId, setProjectId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState({ kind: "info", text: "" });
  const workspace = useRef(null);

  const notify = useCallback((text) => setStatus({ kind: "info", text }), []);
  const fail = useCallback((error) => setStatus({ kind: "error", text: error.message }), []);
  const refresh = useCallback(() => listProjects().then(setProjects).catch(fail), [fail]);

  useEffect(() => {
    if (HOSTED) return; // no StoryBridge server on the public website
    getConfig().then(setConfig).catch(fail);
    refresh();
  }, [fail, refresh]);

  useEffect(() => {
    if (projectId) workspace.current?.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth", block: "start" });
  }, [projectId]);

  async function handleCreate(body) {
    setBusy(true);
    try {
      const project = await createProject(body);
      notify("Story created. Next, add the recording.");
      await refresh();
      setProjectId(project.id);
    } catch (error) {
      fail(error);
    } finally {
      setBusy(false);
    }
  }

  function close() {
    setProjectId(null);
    refresh();
    document.getElementById("your-stories")?.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth" });
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <Hero />
      <div className="site">
        <main id="main" tabIndex={-1}>
          <HowItWorks />

          {HOSTED ? (
            <HostedNotice />
          ) : (
            <section className="panels" aria-label="Your stories and a new story">
              <div className="panel panel-lilac" id="your-stories">
                <p className="eyebrow eyebrow-pink">Your stories</p>
                <h2 className="panel-title">
                  <span className="display">Pick up where</span> <span className="display">you left off.</span>
                </h2>
                <StoryList projects={projects} openId={projectId} onOpen={setProjectId} />
              </div>

              <div className="panel panel-blue" id="start">
                <p className="eyebrow eyebrow-blue">For families and volunteers</p>
                <h2 className="panel-title">
                  <span className="display">Start a new story</span>{" "}
                  <span className="display">for someone you love.</span>
                </h2>
                <NewProjectForm onCreate={handleCreate} busy={busy} />
              </div>
            </section>
          )}

          {projectId && (
            <section ref={workspace} className="workspace" id="workspace" aria-label="The open story">
              <ProjectPage
                key={projectId}
                projectId={projectId}
                config={config}
                notify={notify}
                fail={fail}
                onChanged={refresh}
                onClose={close}
              />
            </section>
          )}
        </main>
      </div>
      <SiteFooter />
      <StatusBar status={status} />
    </>
  );
}
