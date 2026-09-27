# AI Prompt Log — Campus Customs, Homework 4

A running log of the prompts I typed while building this assignment.

**Format.** One section per problem, in order, each with:

- the problem number and title
- at least one prompt I typed, quoted as I typed it
- a follow-up prompt, if the first one was not enough
- when there is a follow-up, one sentence on what was missing after the first prompt

Sections are filled in as each problem is completed, not at the end.

---

## Setup — Environment, data, and project brief

*Prompts typed before Problem 1 began.*

### Prompt

> Alright today we are working in HW 4 folder

### Prompt

> [attached: "data for HW 4.zip"]

### Follow-up

> you have these right: data/campus_customs.db — SQLite database with tables catalogue, inventory, and users (one test user is already there); data/products/ — product images; paths match the catalogue table

What was missing after the first prompt: the summary undercounted the database — there are four tables rather than three (`chat_messages` also exists), three users rather than one, and `image_file_path` is stored relative to `data/`, not the project root.

### Prompt

> yoo claude we are working on a campus customs homework 4 and we will be working through it one problem at a time. this project pertains to a customer website for the campus customs. the frontend of the project needs to use react, vite, and typescript and the backend needs to use python, fastapi, and a pydanticai agent.
>
> database includes the product catalogue, inventory by size, and users. also the product image paths are stored inside the catalogue table. this website needs to allow shoppers to browse products, and create an account, and chat about the merchandise, and also see matching products appear on the page, and finally also get an accurate price and inventory information from local database. i will also be needing you to research yalebulldogblue.com for campus customs style and to take any and all the information that can help
>
> there are a total of 13 problems in this assignment and we will be completing them one problem at a time.
>
> as the last step of the project, we will push the project to a public git hub repo and submit the repo url on canvas. please please please do not commit the database or product image.

### Prompt

> Keep making ammends prompts, and updating the workflow as you feel like best given the objective

### Follow-up

> This homewoek is independent of hw 3, dont let it mislead you

What was missing after the first prompt: the workflow scaffolding had inferred HW4's conventions and AI provider from the neighbouring HW3 folder instead of waiting for HW4's own problem prompts.

---

## Problem 1 — Vibe Coder Prompts

### Prompt

> okay so problem 1, we need to create ai_prompts.md at the start of this assignment and keep it updated as we work through. for each of the problem our file would need a section with the problem number and as well as the title, at least one prompt i typed, and a follow-up prompt if i needed one in that case. also if i use a follow-up, i also need one sentence explaining what was missing after the first prompt. please create the file and set it up for the assignment.

### Follow-up

> Problem 1 – Vibe Coder Prompts:
>
> Okay so problem 1, we need to create AI_prompts.md at the start of this assignment and keep it updated as we work through. For each of the problem our file would need a section with the problem number and as well as the title, at least one prompt I typed, and a follow-up prompt if I needed one in that case. Also If I use a follow-up, I also need one sentence explaining what was missing after the first prompt. Please create the file and set it up for the assignment.

What was missing after the first prompt: the file had been created as `ai_prompts.md`, copying the lowercase spelling of my paraphrased prompt, when the assignment names the file `AI_prompts.md`.

---


## Problem 2 — Analyze the Database

### Prompt

> Okay so for the Problem 2, please have a look at the data/campus_customs.db and then help me understand all the fields in the catalogue, inventory, and users tables. We need to start output/harness.md. also for each table, we need to list its fields and give a short explanation of why each field matters for the shop or the chatbot. Please use the actual database instead of guessing the fields.

## Problem 3 — Build the Campus Customs Website

### Prompt

> Okay so for problem 3, we need to build the Campus Customs website using React, Vite, and TypeScript. Please add a navigation bar with Home, Products, About Us, Log in, and Create account. Also for the Home and About Us, research yalebulldogblue.com for the general Campus Customs style and information, but write the pages in own words through paraphrasing (have it reviewed and edited by me) instead of copying the site's text. Also the Products page needs to show the product images from the catalogue along with the product name, price, and short description. Also each product should open its own detail page with a large image on one side and the full and complete product information on the other side, including the description, the price, and the sizes/stock when available. Please also add a chat interface in the bottom right side of the website. It can be a stub for now because the agent connection comes later. It is also okay to start a simple FastAPI app in backend/main.py for reading products and serving images if needed.

## Problem 4 — Create the Account and Login

### Prompt

> Okay so for problem 4 now, we will be needing a normal create account and login flow.
> The create account should collect first name, last name, email, and password. And the login should use email and password. All the new accounts need to be added to the users table, and all the passwords need to be stored securely rather than as just plain text. The database already has this test user: Email: test@campuscustoms.yale.edu Password: password
> Please do make sure that I can log in with that account and that a newly created account should also work. Also then update output/harness.md to explain how the authentication works, what are the user information stored, and how the passwords are protected.

## Problem 5 — PydanticAI Agent Backend

### Prompt

> Okay so now for problem 5, we need to turn website chat into a PydanticAI agent behind FastAPI being plugged into the front-end chat widget.
> The backend should have these files: backend/main.py, backend/agent.py (this is the agents entry or wiring), backend/tools.py (these are the tools the agent can call), backend/models.py (these are the pydantic or pydantic AI structured types), backend/prompts/prompt.md (these are the system prompts).
> main.py should contain FastAPI app and also the chat route. The frontend should be able to send a chat messages and also receive the agents response including whatever is needed for the products or authentication. The Campus Customs voice and the basic safety instructions should go into prompts/prompt.md. Please use models.py for the Pydantic/PydanticAI structured types needed for the chat and product cards. Make use of the AI model API key. Please also update output/harness.md to explain how the frontend communicates with FastAPI and also how the agent is loaded, including the prompt file and model. The backend needs to run from the backend folder like the following: uvicorn main:app --reload --port 8000
> Only work on Problem 5 for now.

## Problem 6 — Tools: Product Info and Stock

### Prompt

> Aright so now for Problem 6. we need to give the agent tools that look up for the real information from data/campus_customs.db. The agent should to be able to get The Product descriptions, The Prices, The Inventory quantities, and The Inventory by size when a customer asks about a size The database must only be used for this information. The agent should never invent any prices or any quantities. If a size is out of stock, it should clearly communicate that. Please also update the prompts/prompt.md so that the agent knows to use these tools for price and stock questions. Please also add or update the return types in models.py as and when needed. Then also update output/harness.md with all the list of each tool and the reasons for the model fields used for their lookup results, including also why those fields were chosen.

## Problem 7 — Chat Search That Updates the Page

### Prompt

> Okay so now for problem 7, we need the chat to search for the catalogue when a customer asks about a type of product. Such as, if someone asks what shirts do you have?, the agent should search the catalogue and return matching products. The website should also then display those matches as product cards with an image, name, price, and short information. The agent basically needs to return structured product matches so the frontend can render them on the website itself. Also the product cards that appear through the chat should also work like product cards from Problem 3. Clicking one should simply open the single-product detailed page. Please also update the prompts/prompt.md and output/harness.md so that the search result flow is properly documented throughout.

## Problem 8 — Customer Memory

### Prompt

> Okay so now for Problem 8, whenever a shopper is logged in, we will be needing their chat history saved in the database and loaded again whenever they returned. The agent also needs to know who is chatting, including their specific name and email. You may use the agent dependencies or any another clear approach for this and or the tools that the agent could call. I will also need enough page context passed to the agent so that if someone is on the product page and then asks something like do you have this in black? the agent should know which product they are talking about. Maybe we put code into the agents context. Guests should also be able use the chat, but their history does not require to be saved. Please also update output/harness.md with how the chat history is stored all along, and what customer information the agent is seeing, and also how the page context is passed.

## Problem 9 — Usability Improvements

### Prompt

> Okay so now for the Problem 9. We will need to choose and implement the following, firstly two frontend usability improvements, secondly two agent/backend usability improvements.
> The frontend improvements should be the things that make the site look better or a bit easier to use. Whereas, the agent/backend improvements should work on output, and make the agent's output better, more accurate, or more safe. This could also include any new tools or changes that make the agent faster or cheaper. Please create the output/usability.md at first. Then for each improvement, first explain what was added and then why it helps a Campus Customs shopper or the business in any way these are suppose to be my words, so have it reviewed by me pls.
> Please also make sure that all four improvements actually appear in the running application.

## Problem 10 — Style the Website

### Prompt

> Okay so now for problem 10, we will need to include a creative design so the site feels like a real Campus Customs storefront. Please also work on all things such as fonts, and colors, and hierarchy, and motion, and product presentation, and the chat experience. The main goal is to make the design imaginative and also innovative. Please create output/design.md explaining clearly what was changed and why it should help customers stay on the site and buy. Keep the explanation concrete and short (this also needs to be my words, so please write and have it reviewed by me).

## Problem 11 — Site Testing (App Check)

### Prompt

> Alright so now we are starting off with the problem 11, we first of all need to test the live website and also create output/app_check.html which should be accessible be double clicking. It will be needing screenshots and short captions for exactly these three checks which includes, firstly the chat checking the inventory level of a item, while showing the honest stock and also the price information from the database. Secondly, the dynamic search result product cards appearing after a category question such as shirt. Lastly, one of the usability improvements from the Problem 9. The HTML should be having a heading for each check, thee screenshot, and one or two sentences explaining what the screenshot actually proves. Please place the screenshot files in the: output/app_check_images/ Please use the relative paths such as the app_check_images/inventory.png

## Problem 12 — Audit Trail, Safety, Finish Harness

### Prompt

> Okay so now we are working on problem 12, I will be needing an append-only output/audit_trail.json that properly records the agent-loop activity, including the time, and tool name, and short arguments/results, and the stop reason. The file should not be wiped between the runs. I will also need safety rules for the agent in prompts/prompt.md. Finally, please finish output/harness.md so it explains the following things, the model fields in models.py and why they were chosen, the tools and abilities, the safety rules, the loop limits, the result caps, the models, and finally how to run the frontend and backend

## Problem 13 — *(not started)*
