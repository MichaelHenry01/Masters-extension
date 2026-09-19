#This is script for GA

# Your 4 top-performing parents
parent1 = [0.2, 0.25, 0.35, 0.1, 0.05, 0.05] 
parent2 = [0.2753, 0.2475, 0.2574, 0.1099, 0.0688, 0.0411] 
parent3 = [0.2386, 0.1231, 0.3231, 0.1384, 0.0884, 0.0884]
parent4 = [0.2579, 0.1201, 0.2843, 0.1466, 0.0978, 0.0933]

# Put them in a list (ensure the best one is at index 0 for Elitism)
top_4_parents = [parent1, parent2, parent3, parent4]

import random

def generate_next_gen(parents, mutation_rate=0.1):      #Change from 0.3 to 0.1 for the 2nd transition from gen 2 to gen 3
    """
    parents: List of 4 lists (the top 4 performing weight sets)
    returns: List of 8 individuals (1 Elite + 7 New Children)
    """
    
    # 1. Elitism: Keep the best parent exactly as they are
    new_population = [parents[0]] 
    
    # 2. Crossover & Mutation to create 7 children
    while len(new_population) < 8:
        # Pick two different parents randomly
        p1, p2 = random.sample(parents, 2)
        
        # --- ARITHMETIC CROSSOVER ---
        # Create a child by blending p1 and p2
        # alpha is the 'weight' of the first parent
        alpha = random.uniform(0, 1)
        child = []
        for i in range(len(p1)):
            gene = (alpha * p1[i]) + ((1 - alpha) * p2[i])
            child.append(gene)
            
        # --- MUTATION ---
        for i in range(len(child)):
            if random.random() < mutation_rate:
                child[i] += random.uniform(-0.05, 0.05)
        
        # --- CLEAN UP (Normalization & Positivity) ---
        # Ensure no weights are zero or negative
        child = [max(0.01, w) for w in child]
        # Sum to 1.0
        total = sum(child)
        
        # FINAL ROUNDING to 4 decimal places
        child = [round(w / total, 4) for w in child]
        
        # Micro-adjustment to ensure sum is EXACTLY 1.0 after rounding
        # (Rounding can sometimes leave you at 0.9999 or 1.0001)
        diff = round(1.0 - sum(child), 4)
        child[0] = round(child[0] + diff, 4)

        # child = [w / total for w in child]
        
        new_population.append(child)
        
    return new_population


# Generate the next generation (8 individuals)
# We set mutation_rate to 0.1 for the first transition
gen_2_population = generate_next_gen(top_4_parents, mutation_rate=0.1)

# View the results
print(f"Total individuals in Gen 2: {len(gen_2_population)}")
for i, ind in enumerate(gen_2_population):
    # ind is the list of weights; sum(ind) will be 1.0
    print(f"Child {i}: {ind}")