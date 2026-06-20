# Voice-Enabled AI Teaching Assistant

A voice-first AI classroom copilot designed for government school teachers. The system enables hands-free teaching by converting spoken instructions into simplified explanations, interactive quizzes, dynamic educational visuals, and spoken responses. It is optimized for smart-board classrooms and supports Hindi-English mixed interactions (Hinglish).

---

# Tech Stack

## Frontend

### Streamlit

Used to build the classroom interface and smart-board experience.

Features:

* Voice interaction interface
* Dynamic visual rendering
* Quiz display
* Illustration generation
* Teacher-friendly dashboard

---

## Speech-to-Text (STT)

### Sarvam AI

Purpose:

* Convert teacher speech into text
* Support Hindi, English, and Hinglish inputs
* Handle classroom-style spoken instructions

Example:

Teacher:

> "Photosynthesis ko simple Hinglish mein samjhao"

Output:

> "Photosynthesis ko simple Hinglish mein samjhao"

---

## Large Language Models (LLMs)

### Groq

Used for low-latency educational tasks:

* Simple explanations
* Definitions
* Translation
* Dictation
* Basic quiz generation

Benefits:

* Fast response times
* Cost efficient
* Suitable for routine classroom interactions

---

### Gemini 2.5 Flash

Used for advanced educational reasoning:

* Personalized teaching
* Concept maps
* Visual planning
* Comparisons
* Higher-order thinking questions
* Multi-step reasoning

Benefits:

* Strong reasoning capabilities
* High-quality educational content
* Reliable structured outputs

---

## Multi-LLM Routing System

The platform uses an intelligent routing architecture.

Teacher Query
→ Groq Classifier
→ Intent Detection
→ Complexity Analysis
→ Rule Engine
→ Groq or Gemini

Simple requests are routed to Groq.

Complex educational tasks are routed to Gemini.

This improves:

* Response speed
* Cost efficiency
* Educational quality

---

## Text-to-Speech (TTS)

### ElevenLabs

Purpose:

* Convert AI-generated explanations into natural speech
* Deliver classroom-friendly voice responses

Features:

* Human-like voice quality
* High intelligibility
* Interactive teaching experience

---

## Visual Generation Engine

The platform does not rely on static educational images.

Instead, visuals are generated dynamically from structured educational schemas.

### Mermaid

Used for:

* Water Cycle
* Food Chain
* Scientific Processes
* Workflow Diagrams

---

### Dynamic SVG Renderer

Used for:

* Photosynthesis
* Plant Cell
* Solar System
* Human Body Systems
* Science Diagrams

Visuals are assembled dynamically using reusable SVG components.

---

### Plotly

Used for:

* Mathematics
* Graphs
* Statistics
* Data Visualization

---

### HTML/CSS Components

Used for:

* Quiz Cards
* Comparison Tables
* Learning Flashcards
* Vocabulary Boards

---

# Prompt Design

The system follows a structured prompt engineering approach to ensure educational accuracy and consistency.

---

## Classification Prompt

Purpose:

* Detect user intent
* Estimate complexity
* Determine visual requirements

Output Format:

```json
{
  "intent": "",
  "complexity": 1,
  "requires_visual": true,
  "visual_type": ""
}
```

This prompt powers the routing layer.

---

## Concept Simplification Prompt

Purpose:

* Explain concepts in simple Hinglish
* Adapt explanations for school students

Prompt Rules:

* Use Hinglish
* Grade 6–10 friendly
* Maximum 150 words
* Include real-life examples
* Avoid technical jargon
* Maintain educational accuracy

Example:

Input:

> Explain gravity

Output:

> Gravity ek force hai jo har object ko Earth ki taraf attract karti hai. Jab aap ball ko upar throw karte ho, woh wapas neeche aati hai because of gravity.

---

## Quiz Generation Prompt

Purpose:

* Generate classroom-ready MCQs
* Adapt difficulty based on student level

Output Format:

```json
{
  "questions": [
    {
      "question": "",
      "options": [],
      "answer": ""
    }
  ]
}
```

---

## Visual Planning Prompt

Purpose:

* Determine the most appropriate visual format

Possible Outputs:

* Process Diagram
* Science Diagram
* Timeline
* Comparison View
* Mathematical Graph

This ensures every concept receives the most effective visual representation.

---

# Localization Strategy

The platform is designed specifically for multilingual Indian classrooms.

---

## Hinglish Support

Students and teachers often communicate using a mix of Hindi and English.

Example:

Teacher:

> "Water cycle ko simple English aur Hindi mix mein explain karo"

The system naturally responds in Hinglish.

---

## Language-Aware Speech Recognition

Sarvam AI is used because it performs well on:

* Hindi
* English
* Hinglish
* Indian accents

---

## Contextual Classroom Language

The assistant avoids overly formal academic language.

Instead it uses:

* Everyday examples
* Familiar vocabulary
* Student-friendly explanations

Example:

Instead of:

> Photosynthesis is the biochemical conversion of light energy into chemical energy.

The assistant says:

> Plants sunlight ka use karke apna food banate hain. Is process ko photosynthesis kehte hain.

---

## Inclusive Learning Design

The platform supports:

* Visual learners through diagrams
* Auditory learners through voice explanations
* Interactive learners through quizzes

This ensures a more accessible classroom experience for diverse student groups.

---

# Key Innovations

* Voice-first classroom interaction
* Hinglish educational explanations
* Multi-LLM intelligent routing
* Dynamic visual generation engine
* Smart-board optimized UI
* Classroom-ready quiz generation
* Real-time speech interaction
* Scalable localization framework

The result is a practical AI teaching assistant that helps educators deliver engaging, accessible, and interactive learning experiences with minimal manual effort.
